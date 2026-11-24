"""Synthetic immutable artifact admission tests; no real repository writes."""
import copy
import sys
import subprocess
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.orchestration import artifact_gateway as g
from wii_ai_golf.orchestration import broker as b
from wii_ai_golf.orchestration import github_store as storage
from wii_ai_golf.orchestration import state as model
from test_v3_github_store import FakeGit, BASE, BRANCH, initial, progress, task

BASE_CODE = "1" * 40
HEAD_CODE = "2" * 40
BASE_TREE = "3" * 40
HEAD_TREE = "4" * 40


def row(path, mode="100644", sha="5", kind="blob"):
    return {"path": path, "mode": mode, "sha": sha * 40, "type": kind}


class TreeFixture:
    def __init__(self):
        self.objects = {
            "commits/" + BASE_CODE: {"sha": BASE_CODE, "tree": {"sha": BASE_TREE},
                                     "parents": []},
            "commits/" + HEAD_CODE: {"sha": HEAD_CODE, "tree": {"sha": HEAD_TREE},
                                     "parents": [{"sha": BASE_CODE}]},
            "trees/" + BASE_TREE + "?recursive=1": {
                "sha": BASE_TREE, "truncated": False,
                "tree": [row("src", "040000", "6", "tree"), row("src/a"), row("src/b")]},
            "trees/" + HEAD_TREE + "?recursive=1": {
                "sha": HEAD_TREE, "truncated": False,
                "tree": [row("src", "040000", "7", "tree"), row("src/a", sha="8"), row("src/b")]},
        }
        self.reads = []

    @property
    def before(self):
        return self.objects["trees/" + BASE_TREE + "?recursive=1"]

    @property
    def after(self):
        return self.objects["trees/" + HEAD_TREE + "?recursive=1"]

    def __call__(self, method, path, payload):
        assert method == "GET" and payload is None
        assert path.startswith("/repos/owner/repo/git/")
        self.reads.append(path)
        return copy.deepcopy(self.objects[path.split("/git/", 1)[1]])


class ExactPushTests(unittest.TestCase):
    def test_git_receive_pack_exact_old_ref_in_disposable_local_fixture(self):
        # Actual local Git protocol, never a network or production ref.
        # Replace only the host's fixed remote with a temporary bare repository.
        with tempfile.TemporaryDirectory() as d:
            work, remote = Path(d) / "work", Path(d) / "remote.git"
            def git(*args, cwd=None, check=True):
                return subprocess.run(["git", *map(str, args)], cwd=cwd,
                                      capture_output=True, text=True, check=check)
            git("init", "-q", work)
            git("init", "-q", "--bare", remote)
            def commit(message):
                git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                    "commit", "-q", "--allow-empty", "-m", message, cwd=work)
                return git("rev-parse", "HEAD", cwd=work).stdout.strip()
            base = commit("base")
            head = commit("child")
            tree = git("rev-parse", base + "^{tree}", cwd=work).stdout.strip()
            sibling = git("-c", "user.name=Fixture", "-c",
                          "user.email=fixture@example.invalid",
                          "commit-tree", tree, "-p", base, "-m", "sibling", cwd=work).stdout.strip()
            target = "orchestration/v3-publication-test-unit"
            ref = "refs/heads/" + target
            cmd = g.PublicationCommand("owner/repo", BRANCH, BASE, "test-intent",
                                       target, base, head, "a" * 64)
            args = g.exact_push_arguments(cmd)
            self.assertEqual(args[-2], "https://github.com/owner/repo.git")
            self.assertEqual(args[-1], head + ":" + ref)
            self.assertIn("--force-with-lease=" + ref + ":" + base, args)
            args[-2] = str(remote)
            def observed():
                return git("--git-dir=" + str(remote), "rev-parse", ref).stdout.strip()
            git("push", "-q", remote, base + ":" + ref, cwd=work)
            self.assertEqual(git(*args, cwd=work, check=False).returncode, 0)
            self.assertEqual(observed(), head)
            # Seed sibling in the disposable bare repository, then move target
            # locally to simulate a competing writer. The exact lease must fail.
            git("push", "-q", remote, sibling + ":refs/heads/fixture-sibling", cwd=work)
            git("--git-dir=" + str(remote), "update-ref", ref, sibling)
            self.assertNotEqual(git(*args, cwd=work, check=False).returncode, 0)
            self.assertEqual(observed(), sibling)
            git("--git-dir=" + str(remote), "update-ref", "-d", ref)
            self.assertNotEqual(git(*args, cwd=work, check=False).returncode, 0)
            self.assertNotEqual(git("--git-dir=" + str(remote), "show-ref", "--verify",
                                    ref, check=False).returncode, 0)
            for target in ("main", "orchestration/v3-state", "refs/heads/main"):
                with self.assertRaises(g.ArtifactError):
                    g.PublicationCommand("owner/repo", BRANCH, BASE, "test-intent",
                                         target, base, head, "a" * 64)


class DurableJournalTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "dispatch.sqlite"
        self.journal = g.DurablePublicationJournal.create(self.path, "owner/repo", BRANCH)
        self.command = g.PublicationCommand("owner/repo", BRANCH, BASE, "intent",
            "orchestration/v3-publication-test-unit", BASE_CODE, HEAD_CODE, "a" * 64)

    def reopen(self):
        return g.DurablePublicationJournal(self.path, "owner/repo", BRANCH)

    def test_explicit_provision_identity_and_conflicting_binding(self):
        c = self.command
        self.assertTrue(self.journal.reserve_once(c.key, c.binding))
        self.assertFalse(self.reopen().reserve_once(c.key, c.binding))
        with self.assertRaises(g.ArtifactError):
            self.reopen().reserve_once(c.key, "b" * 64)
        with self.assertRaises(g.ArtifactError):
            g.DurablePublicationJournal.create(self.path, "owner/repo", BRANCH)
        with self.assertRaises(g.ArtifactError):
            g.DurablePublicationJournal(self.path, "other/repo", BRANCH)
        missing = self.path.with_name("missing.sqlite")
        with self.assertRaises(g.ArtifactError):
            g.DurablePublicationJournal(missing, "owner/repo", BRANCH)
        self.assertFalse(missing.exists())

    def test_cross_connection_reservation_and_cancellation_race(self):
        c = self.command
        barrier = threading.Barrier(2)
        def reserve():
            j = self.reopen()
            barrier.wait(timeout=10)
            return j.reserve_once(c.key, c.binding)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [pool.submit(reserve) for _ in range(2)]
            self.assertCountEqual([x.result(timeout=20) for x in results], [True, False])
        barrier = threading.Barrier(2)
        def advance(method):
            j = self.reopen()
            barrier.wait(timeout=10)
            try:
                getattr(j, method)(c)
                return method
            except g.ArtifactError:
                return "denied"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [pool.submit(advance, m) for m in ("begin", "cancel_before_send")]
            observed = [x.result(timeout=20) for x in results]
        self.assertEqual(observed.count("denied"), 1)
        self.assertIn(self.reopen().phase(c), ("SENDING", "CANCELLED"))
        self.assertFalse(self.reopen().reserve_once(c.key, c.binding))

    def test_abrupt_process_death_after_begin_is_never_retried_or_settled(self):
        c = self.command
        self.journal.reserve_once(c.key, c.binding)
        root = Path(__file__).resolve().parents[1]
        script = """
import os
import sys
sys.path.insert(0, sys.argv[1])
from wii_ai_golf.orchestration import artifact_gateway as g
c = g.PublicationCommand(*sys.argv[3:])
j = g.DurablePublicationJournal(sys.argv[2], c.repository, c.queue_branch)
j.begin(c)
os._exit(73)
"""
        result = subprocess.run([sys.executable, "-I", "-c", script, str(root / "src"),
            str(self.path), c.repository, c.queue_branch, c.queue_head, c.intent,
            c.target, c.base, c.head, c.manifest_digest], capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 73, result.stderr)
        j = self.reopen()
        self.assertEqual(j.phase(c), "SENDING")
        sends, reads = [], []
        executor = g.DurablePublicationExecutor(c.repository, c.queue_branch, j,
            sends.append, reads.append)
        with self.assertRaises(g.ArtifactError):
            executor.reserve(c)
        with self.assertRaises(g.ArtifactError):
            executor.cancel_before_send(c)
        self.assertIsNone(executor.observe(c))
        self.assertEqual((sends, reads), ([], []))

    def test_independent_ref_reader_checks_identity_and_repository(self):
        c = self.command
        calls = []
        response = {"ref": "refs/heads/" + c.target,
                    "object": {"type": "commit", "sha": c.head}}
        def transport(method, endpoint, payload):
            calls.append((method, endpoint, payload))
            return response
        reader = g.GitHubPublicationRefReader(transport, c.repository)
        self.assertEqual(reader(c), c.head)
        self.assertEqual(calls, [("GET", "/repos/owner/repo/git/ref/heads/" + c.target, None)])
        response["ref"] = "refs/heads/main"
        with self.assertRaises(g.ArtifactError):
            reader(c)
        with self.assertRaises(g.ArtifactError):
            g.GitHubPublicationRefReader(transport, "other/repo")(c)


class InspectorTests(unittest.TestCase):
    def setUp(self):
        self.git = TreeFixture()
        self.inspector = g.GitHubTreeInspector(self.git, "owner/repo")

    def inspect(self):
        return self.inspector.inspect(BASE_CODE, HEAD_CODE)

    def test_complete_immutable_diff(self):
        changes = self.inspect()
        self.assertEqual(changes, [{"path": "src/a",
                                    "before": {"mode": "100644", "sha": "5" * 40},
                                    "after": {"mode": "100644", "sha": "8" * 40}}])
        self.assertEqual(len(self.git.reads), 4)
        self.assertEqual(g.validate_manifest(changes, ["src/a"]), changes)
        for wrong in (["src"], ["src/A"], ["src/ab"], []):
            with self.assertRaises(g.ArtifactError):
                g.validate_manifest(changes, wrong)

    def test_truncated_wrong_identity_and_non_direct_parent(self):
        self.git.after["truncated"] = True
        with self.assertRaises(g.ArtifactError):
            self.inspect()
        self.git.after["truncated"] = False
        self.git.after["sha"] = BASE_TREE
        with self.assertRaises(g.ArtifactError):
            self.inspect()
        self.git.after["sha"] = HEAD_TREE
        self.git.objects["commits/" + HEAD_CODE]["parents"] = [
            {"sha": BASE_CODE}, {"sha": "9" * 40}]
        with self.assertRaises(g.ArtifactError):
            self.inspect()

    def test_symlink_gitlink_and_case_alias_rejected(self):
        for mode, kind in (("120000", "blob"), ("160000", "commit")):
            self.git.after["tree"][1] = row("src/a", mode, "8", kind)
            with self.assertRaises(g.ArtifactError):
                self.inspect()
        self.git.after["tree"][1] = row("src/A", sha="8")
        with self.assertRaises(g.ArtifactError):
            self.inspect()

    def test_rename_cannot_hide_unowned_deletion(self):
        self.git.after["tree"][1] = row("src/new", sha="8")
        changes = self.inspect()
        self.assertEqual([c["path"] for c in changes], ["src/a", "src/new"])
        with self.assertRaises(g.ArtifactError):
            g.validate_manifest(changes, ["src/new"])

    def test_directory_alias_and_unrepresented_empty_tree(self):
        self.git.after["tree"] = [row("SRC", "040000", "7", "tree"), row("SRC/a", sha="8")]
        with self.assertRaises(g.ArtifactError):
            self.inspect()
        self.git.after["tree"] = [row("src", "040000", "7", "tree"), row("src/a", sha="8"),
                                  row("src/b"), row("empty", "040000", "9", "tree")]
        with self.assertRaises(g.ArtifactError):
            self.inspect()


class GatewayBrokerTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeGit()
        self.store = storage.GitHubStore(self.api, "owner/repo", BRANCH)
        self.store.bootstrap_test(BASE, initial(), "seed")
        self.git = TreeFixture()
        self.inspector = g.GitHubTreeInspector(self.git, "owner/repo")
        self.now = 1
        self.allow = True
        self.seen = []
        self.tokens = {"a": "a" * 40, "b": "b" * 40, "m": "m" * 40}
        self.credentials = b.Credentials([
            (b.token_digest(self.tokens["a"]), b.Principal("alpha", frozenset({"S000"}))),
            (b.token_digest(self.tokens["b"]), b.Principal("beta", frozenset({"S000"}))),
            (b.token_digest(self.tokens["m"]), b.Principal("manager", frozenset({"S000"}), True)),
        ])
        def review(principal, action, payload, current):
            self.seen.append(copy.deepcopy(payload))
            return self.allow
        self.broker = b.Broker(self.store, self.credentials, clock=lambda: self.now,
                               reviewer=review, inspector=self.inspector)

    def req(self, who, request, action, payload=None):
        return self.broker.request(self.tokens[who], request, action, payload or {})

    def proposal(self, who="a"):
        lease = self.req(who, "claim", "acquire")["lease"]
        return {**{k: lease[k] for k in ("task", "run_id", "fence")},
                "base": BASE_CODE, "head": HEAD_CODE,
                "progress": {**progress(), "head": HEAD_CODE}}

    def test_acceptance_is_durable_atomic_and_not_source_promotion(self):
        proposal = self.proposal()
        self.now = 2
        accepted = self.req("a", "artifact", "accept_artifact", proposal)
        record = accepted["artifact"]
        snap = self.store.read()
        self.assertFalse(accepted["source_promoted"])
        self.assertEqual(snap.envelope["artifacts"][accepted["operation"]], record)
        self.assertEqual(snap.state["tasks"]["a"]["checkpoint"]["head"], HEAD_CODE)
        self.assertEqual(snap.envelope["receipts"][accepted["operation"]]["revision"],
                         record["revision"])
        self.assertEqual(self.seen[-1]["changes"], record["changes"])
        self.assertEqual(self.seen[-1]["goal_sha"], snap.state["oversight"]["goal_sha"])
        self.assertEqual(self.broker.status(self.tokens["m"])["accepted_artifacts"],
                         snap.envelope["artifacts"])
        self.now = 3
        lease = {k: proposal[k] for k in ("task", "run_id", "fence")}
        self.req("a", "finish", "finish", {**lease, "outcome": "OPEN", "progress": progress()})
        self.assertEqual(self.store.read().envelope["artifacts"][accepted["operation"]], record)

    def test_ordinary_checkpoint_not_artifact_and_no_forged_manifest(self):
        proposal = self.proposal()
        self.req("a", "ordinary", "renew",
                 {k: proposal[k] for k in ("task", "run_id", "fence", "progress")})
        self.assertEqual(self.store.read().envelope["artifacts"], {})
        with self.assertRaises(b.AdmissionError):
            self.req("a", "fake", "accept_artifact", {**proposal, "changes": []})

    def test_scope_owner_manager_and_expiry_gates(self):
        proposal = self.proposal()
        count = self.api.patch_count
        with self.assertRaises(b.AdmissionError):
            self.req("b", "stolen", "accept_artifact", proposal)
        self.git.after["tree"][2] = row("src/b", sha="9")
        with self.assertRaises(g.ArtifactError):
            self.req("a", "outside", "accept_artifact", proposal)
        self.assertEqual(self.api.patch_count, count)
        manager = self.proposal("m")
        with self.assertRaises(b.AdmissionError):
            self.req("m", "not-source", "accept_artifact", manager)
        self.now = 121
        with self.assertRaises(model.LeaseError):
            self.req("a", "expired", "accept_artifact", proposal)
        self.assertEqual(self.store.read().envelope["artifacts"], {})

    def test_review_denial_and_expiry_during_review(self):
        proposal = self.proposal()
        self.allow = False
        with self.assertRaises(b.AdmissionError):
            self.req("a", "denied", "accept_artifact", proposal)
        def slow(*args):
            self.now = 121
            return True
        other = b.Broker(self.store, self.credentials, clock=lambda: self.now,
                         reviewer=slow, inspector=self.inspector)
        with self.assertRaises(model.LeaseError):
            other.request(self.tokens["a"], "late", "accept_artifact", proposal)
        self.assertEqual(self.store.read().envelope["artifacts"], {})

    def test_lost_response_replay_and_journal_tamper(self):
        proposal = self.proposal()
        self.api.lose_response = True
        accepted = self.req("a", "artifact", "accept_artifact", proposal)
        self.assertTrue(accepted["replayed"])
        patches = self.api.patch_count
        self.now = 121
        replay = self.req("a", "artifact", "accept_artifact", proposal)
        self.assertEqual(replay["artifact"], accepted["artifact"])
        self.assertEqual(self.api.patch_count, patches)
        self.assertFalse(replay["source_promoted"])
        forged = copy.deepcopy(self.store.read().envelope)
        forged["artifacts"][accepted["operation"]]["manifest_digest"] = "0" * 64
        with self.assertRaises(storage.StoreError):
            storage.validate_envelope(forged)

    def test_missing_inspector_and_wrong_checkpoint_reject(self):
        proposal = self.proposal()
        other = b.Broker(self.store, self.credentials, clock=lambda: self.now,
                         reviewer=lambda *args: True)
        with self.assertRaises(b.AdmissionError):
            other.request(self.tokens["a"], "missing", "accept_artifact", proposal)
        proposal["progress"]["head"] = BASE_CODE
        with self.assertRaises(b.AdmissionError):
            self.req("a", "wrong", "accept_artifact", proposal)


    def publication(self):
        proposal = self.proposal()
        accepted = self.req("a", "artifact", "accept_artifact", proposal)
        payload = {k: proposal[k] for k in ("task", "run_id", "fence")}
        payload.update(artifact=accepted["operation"],
                       target="orchestration/v3-publication-test-unit")
        return payload

    def maintenance(self, observer):
        credentials = b.Credentials([
            (b.token_digest("s" * 40), b.Principal("sweeper", frozenset(), False, True))
        ])
        return b.Broker(self.store, credentials, clock=lambda: self.now,
                        publication_observer=observer)

    def test_publication_intent_freezes_all_mutations_and_replay(self):
        payload = self.publication()
        result = self.req("a", "prepare", "prepare_publication", payload)
        key = result["operation"]
        self.assertFalse(result["source_promoted"])
        self.assertEqual(self.store.read().envelope["publications"][key],
                         result["publication"])
        self.assertEqual(self.broker.status(self.tokens["b"])["eligible"], [])
        count = self.api.patch_count
        with self.assertRaisesRegex(storage.StoreError, "unresolved publication"):
            storage.archive_snapshot(self.store.read())
        with self.assertRaisesRegex(storage.StoreError, "unresolved publication"):
            self.store.stage_archive(self.store.read())
        with self.assertRaisesRegex(storage.StoreError, "unresolved publication"):
            self.store.archive_checkpoint(self.store.read(), "archive-pending")
        self.assertEqual(self.api.patch_count, count)
        self.assertTrue(self.req("a", "prepare", "prepare_publication", payload)["replayed"])
        for action, body in (("acquire", {}), ("renew", {k: payload[k] for k in
                             ("task", "run_id", "fence")}),
                             ("prepare_publication", payload),
                             ("resolve_publication", {"intent": key})):
            with self.assertRaises(b.AdmissionError):
                self.req("a", "new-" + action, action, body)
        snap = self.store.read()
        proposed = model.sweep(snap.state, self.now + 1)
        with self.assertRaises(storage.StoreError):
            self.store.publish(snap, proposed, "bypass")
        self.assertEqual(self.api.patch_count, count)

    def test_only_settled_outcome_resolves_even_after_expiry(self):
        payload = self.publication()
        key = self.req("a", "prepare", "prepare_publication", payload)["operation"]
        self.now = 121
        body = {"intent": key}
        for observation in (None, "9" * 40):
            with self.assertRaises(b.AdmissionError):
                self.maintenance(lambda *args: observation).request(
                    "s" * 40, "resolve", "resolve_publication", body)
        self.assertEqual(storage.pending_publication(self.store.read().envelope), key)
        m = self.maintenance(lambda row, record: record["head"])
        result = m.request("s" * 40, "resolve", "resolve_publication", body)
        snap = self.store.read()
        self.assertIsNone(storage.pending_publication(snap.envelope))
        self.assertEqual(snap.envelope["publications"][key]["resolution"],
                         {"operation": result["operation"], "observed_head": HEAD_CODE})
        self.assertEqual(snap.state["tasks"]["a"]["status"], "OPEN")
        count = self.api.patch_count
        self.assertTrue(m.request("s" * 40, "resolve", "resolve_publication", body)["replayed"])
        self.assertEqual(self.api.patch_count, count)

    def test_wrong_owner_target_and_expiry_deny_intent(self):
        payload = self.publication()
        count = self.api.patch_count
        with self.assertRaises(b.AdmissionError):
            self.req("b", "stolen", "prepare_publication", payload)
        with self.assertRaises(b.AdmissionError):
            self.req("a", "production", "prepare_publication", {**payload, "target": "main"})
        self.now = 121
        with self.assertRaises(model.LeaseError):
            self.req("a", "expired", "prepare_publication", payload)
        self.assertEqual(self.api.patch_count, count)

    def test_settled_base_is_not_a_retry_grant(self):
        payload = self.publication()
        key = self.req("a", "prepare", "prepare_publication", payload)["operation"]
        self.maintenance(lambda row, record: record["base"]).request(
            "s" * 40, "resolve", "resolve_publication", {"intent": key})
        with self.assertRaises(storage.StoreError):
            self.req("a", "second-attempt", "prepare_publication", payload)
        snap = self.store.read()
        tampered = copy.deepcopy(snap.envelope)
        tampered["publications"][key]["resolution"]["observed_head"] = "9" * 40
        with self.assertRaises(storage.StoreError):
            storage.validate_envelope(tampered)

    def test_review_denial_and_expiry_during_publication_review(self):
        payload = self.publication()
        self.allow = False
        with self.assertRaises(b.AdmissionError):
            self.req("a", "denied", "prepare_publication", payload)
        def slow(*args):
            self.now = 121
            return True
        other = b.Broker(self.store, self.credentials, clock=lambda: self.now, reviewer=slow)
        with self.assertRaises(model.LeaseError):
            other.request(self.tokens["a"], "late", "prepare_publication", payload)
        self.assertEqual(self.store.read().envelope["publications"], {})

    def test_publication_requires_settlement_headroom(self):
        payload = self.publication()
        snap = self.store.read()
        count = self.api.patch_count
        # Make the reserve larger than the remaining bytes without making
        # the current valid snapshot unreadable.
        used = len(storage.canonical(snap.envelope))
        with patch.object(storage, "MAX_LEDGER", used + storage.SETTLEMENT_RESERVE):
            with self.assertRaisesRegex(storage.StoreError, "settlement reserve"):
                self.req("a", "prepare", "prepare_publication", payload)
            self.assertEqual(self.store.read().head, snap.head)
            self.assertEqual(self.api.patch_count, count)
        key = self.req("a", "prepare", "prepare_publication", payload)["operation"]
        pending = self.store.read()
        used = len(storage.canonical(pending.envelope))
        self.now = 121
        with patch.object(storage, "MAX_LEDGER", used + storage.SETTLEMENT_RESERVE):
            self.maintenance(lambda row, record: record["head"]).request(
                "s" * 40, "resolve", "resolve_publication", {"intent": key})
            self.assertIsNone(storage.pending_publication(self.store.read().envelope))
            self.assertEqual(self.store.read().state["tasks"]["a"]["status"], "OPEN")



class HotGatewayTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeGit()
        self.store = storage.GitHubStore(self.api, "owner/repo", BRANCH)
        self.store.bootstrap_test(BASE, initial(), "seed")
        self.store.initialize_hot(self.store.read(), "hot-seed")
        self.git = TreeFixture()
        self.inspector = g.GitHubTreeInspector(self.git, "owner/repo")
        self.now = 1
        self.allow = True
        self.observed = None
        self.credentials = b.Credentials([
            (b.token_digest("a" * 40), b.Principal("alpha", frozenset({"S000"}))),
            (b.token_digest("b" * 40), b.Principal("beta", frozenset({"S000"}))),
            (b.token_digest("s" * 40), b.Principal("maintenance", frozenset(), False, True)),
            (b.token_digest("r" * 40), b.Principal("operator", frozenset(), read_only=True)),
        ])
        self.reopen()

    def reopen(self):
        self.store = storage.GitHubStore(self.api, "owner/repo", BRANCH)
        self.broker = b.Broker(self.store, self.credentials, hot=True, clock=lambda: self.now,
                               reviewer=lambda *args: self.allow, inspector=self.inspector,
                               publication_observer=lambda *args: self.observed,
                               history_cursor_key=b"k" * 32)

    def req(self, who, request, action, payload=None):
        return self.broker.request(who * 40, request, action, payload or {})

    def accept(self):
        lease = self.req("a", "claim", "acquire")["lease"]
        proposal = {**{k: lease[k] for k in ("task", "run_id", "fence")},
                    "base": BASE_CODE, "head": HEAD_CODE,
                    "progress": {**progress(), "head": HEAD_CODE}}
        accepted = self.req("a", "artifact", "accept_artifact", proposal)
        payload = {k: proposal[k] for k in ("task", "run_id", "fence")}
        payload.update(artifact=accepted["operation"],
                       target="orchestration/v3-publication-test-unit")
        return proposal, accepted, payload

    def pending(self):
        _, _, payload = self.accept()
        return self.req("a", "prepare", "prepare_publication", payload)["operation"]

    def executor(self, markers, sends, send=None, reserve=None, repository="owner/repo"):
        def claim(key, binding):
            if key in markers:
                return False
            markers[key] = binding
            return True
        return g.PublicationExecutor(repository, BRANCH, reserve or claim,
                                     send or sends.append)

    def test_dispatch_is_host_only_fenced_single_send_and_not_settlement(self):
        intent = self.pending()
        markers, sends = {}, []
        executor = self.executor(markers, sends)
        pinned = self.store.read_hot()
        for who in ("a", "b", "r"):
            with self.assertRaises(b.AdmissionError):
                self.broker.dispatch_publication(who * 40, intent, executor)
        with self.assertRaises(b.AdmissionError):
            self.req("s", "dispatch", "dispatch_publication", {"intent": intent})
        with self.assertRaises(b.AdmissionError):
            self.broker.dispatch_publication("s" * 40, "wrong", executor)
        with self.assertRaises(g.ArtifactError):
            self.broker.dispatch_publication("s" * 40, intent,
                self.executor(markers, sends, repository="other/repo"))
        self.assertEqual(markers, {})
        result = self.broker.dispatch_publication("s" * 40, intent, executor)
        self.assertEqual(result, {"attempted": True, "settled": False, "intent": intent})
        self.assertEqual(len(sends), 1)
        command = sends[0]
        self.assertEqual((command.base, command.head, command.queue_head),
                         (BASE_CODE, HEAD_CODE, pinned.head))
        self.assertEqual(markers, {command.key: command.binding})
        self.assertEqual(self.store.read_hot().head, pinned.head)
        self.reopen()
        with self.assertRaises(g.ArtifactError):
            self.broker.dispatch_publication("s" * 40, intent, self.executor(markers, sends))
        self.assertEqual(len(sends), 1)
        self.assertEqual(self.store.read_hot().manifest["pending_intent"], intent)
        self.observed = HEAD_CODE
        self.req("s", "settle", "resolve_publication", {"intent": intent})
        with self.assertRaises(b.AdmissionError):
            self.broker.dispatch_publication("s" * 40, intent, executor)

    def test_dispatch_expiry_after_marker_and_uncertain_send_never_retries(self):
        intent = self.pending()
        sends, markers = [], {}
        def slow_claim(key, binding):
            markers[key] = binding
            self.now = 121
            return True
        with self.assertRaises(model.LeaseError):
            self.broker.dispatch_publication("s" * 40, intent,
                self.executor(markers, sends, reserve=slow_claim))
        self.assertEqual(len(markers), 1)
        self.assertEqual(sends, [])
        self.assertEqual(self.store.read_hot().manifest["pending_intent"], intent)
        self.now = 2
        with self.assertRaises(g.ArtifactError):
            self.broker.dispatch_publication("s" * 40, intent, self.executor(markers, sends))
        # A separate fixture models a fresh intent after an ambiguous send.
        self.setUp()
        intent = self.pending()
        markers, sends = {}, []
        def lost(command):
            sends.append(command)
            raise TimeoutError("private output must never be surfaced")
        with self.assertRaisesRegex(g.DispatchUncertain, "^dispatch outcome uncertain; do not retry$"):
            self.broker.dispatch_publication("s" * 40, intent,
                self.executor(markers, sends, send=lost))
        self.reopen()
        with self.assertRaises(g.ArtifactError):
            self.broker.dispatch_publication("s" * 40, intent, self.executor(markers, sends))
        self.assertEqual(len(sends), 1)
        self.assertEqual(self.store.read_hot().manifest["pending_intent"], intent)
        with self.assertRaises(b.AdmissionError):
            self.req("s", "ambiguous", "resolve_publication", {"intent": intent})

    def test_dispatch_rechecks_complete_manifest_and_semantic_review(self):
        intent = self.pending()
        markers, sends = {}, []
        executor = self.executor(markers, sends)
        self.allow = False
        with self.assertRaises(b.AdmissionError):
            self.broker.dispatch_publication("s" * 40, intent, executor)
        self.allow = True
        self.git.after["tree"][2] = row("src/b", sha="9")
        with self.assertRaises(b.AdmissionError):
            self.broker.dispatch_publication("s" * 40, intent, executor)
        self.git.after["tree"][2] = row("src/b")
        self.now = 121
        with self.assertRaises(model.LeaseError):
            self.broker.dispatch_publication("s" * 40, intent, executor)
        self.assertEqual(markers, {})
        self.assertEqual(sends, [])

    def durable_executor(self, path, send, read, create=False):
        journal_type = g.DurablePublicationJournal
        journal = (journal_type.create if create else journal_type)(path, "owner/repo", BRANCH)
        executor = g.DurablePublicationExecutor("owner/repo", BRANCH, journal, send, read)
        self.broker = b.Broker(self.store, self.credentials, hot=True, clock=lambda: self.now,
            reviewer=lambda *args: self.allow, inspector=self.inspector,
            publication_observer=executor, history_cursor_key=b"k" * 32)
        return executor

    def test_durable_broker_acknowledgment_requires_independent_exact_ref(self):
        intent = self.pending()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "dispatch.sqlite"
            sends = []
            observed = [BASE_CODE]
            def send(command):
                sends.append(command)
                return True
            executor = self.durable_executor(path, send, lambda c: observed[0], create=True)
            with self.assertRaises(b.AdmissionError):
                self.req("s", "early", "resolve_publication", {"intent": intent})
            self.broker.dispatch_publication("s" * 40, intent, executor)
            self.assertEqual(len(sends), 1)
            self.assertEqual(executor._journal.phase(sends[0]), "ACKNOWLEDGED")
            self.reopen()
            executor = self.durable_executor(path, send, lambda c: observed[0])
            with self.assertRaises(g.ArtifactError):
                self.broker.dispatch_publication("s" * 40, intent, executor)
            with self.assertRaises(g.ArtifactError):
                self.broker.cancel_publication_dispatch("s" * 40, intent)
            with self.assertRaises(b.AdmissionError):
                self.req("s", "wrong-ref", "resolve_publication", {"intent": intent})
            observed[0] = HEAD_CODE
            self.now = 121
            self.req("s", "settle", "resolve_publication", {"intent": intent})
            self.assertIsNone(self.store.read_hot().manifest["pending_intent"])
            self.assertEqual(len(sends), 1)

    def test_durable_broker_cancel_before_send_or_after_expiry(self):
        intent = self.pending()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "dispatch.sqlite"
            sends = []
            executor = self.durable_executor(path, sends.append, lambda c: BASE_CODE, create=True)
            for who in ("a", "r"):
                with self.assertRaises(b.AdmissionError):
                    self.broker.cancel_publication_dispatch(who * 40, intent)
            result = self.broker.cancel_publication_dispatch("s" * 40, intent)
            self.assertFalse(result["settled"])
            self.assertEqual(self.store.read_hot().manifest["pending_intent"], intent)
            with self.assertRaises(g.ArtifactError):
                self.broker.dispatch_publication("s" * 40, intent, executor)
            self.reopen()
            self.durable_executor(path, sends.append, lambda c: BASE_CODE)
            self.now = 121
            self.req("s", "settle", "resolve_publication", {"intent": intent})
            self.assertEqual(sends, [])
            self.assertIsNone(self.store.read_hot().manifest["pending_intent"])
            self.assertEqual(self.store.read_hot().state["tasks"]["a"]["status"], "OPEN")

    def test_durable_broker_uncertain_even_if_ref_appears_to_match(self):
        intent = self.pending()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "dispatch.sqlite"
            sends, reads = [], []
            def send(command):
                sends.append(command)
                raise TimeoutError("private diagnostic")
            def read(command):
                reads.append(command)
                return HEAD_CODE
            executor = self.durable_executor(path, send, read, create=True)
            with self.assertRaises(g.DispatchUncertain):
                self.broker.dispatch_publication("s" * 40, intent, executor)
            self.reopen()
            executor = self.durable_executor(path, send, read)
            with self.assertRaises(g.ArtifactError):
                self.broker.cancel_publication_dispatch("s" * 40, intent)
            with self.assertRaises(b.AdmissionError):
                self.req("s", "not-settled", "resolve_publication", {"intent": intent})
            self.assertEqual((len(sends), len(reads)), (1, 0))
            self.assertEqual(self.store.read_hot().manifest["pending_intent"], intent)

    def test_hot_publication_freeze_reopen_expire_settle_and_history(self):
        proposal, accepted, payload = self.accept()
        intent = self.req("a", "prepare", "prepare_publication", payload)
        key = intent["operation"]
        pinned = self.store.read_hot()
        self.assertEqual(pinned.manifest["pending_intent"], key)
        self.reopen()
        self.assertEqual(self.store.hot_lookup("artifact", accepted["operation"]),
                         accepted["artifact"])
        self.assertEqual(self.store.hot_publication_at(self.store.read_hot(), key),
                         intent["publication"])
        self.assertEqual(self.broker.status("b" * 40)["eligible"], [])
        count = self.api.patch_count
        with self.assertRaises(b.AdmissionError):
            self.req("b", "new", "acquire")
        with self.assertRaises(b.AdmissionError):
            self.req("s", "sweep", "sweep")
        with self.assertRaises(storage.StoreError):
            self.store.publish_hot(pinned, "bypass", "a" * 64,
                                   lambda state, exists: model.sweep(state, 2))
        endpoint = b.OperatorReadEndpoint("wii-golf", self.broker)
        self.assertEqual(endpoint.handle("GET", "/v3/projects/wii-golf/read-v2/status",
                                         "Bearer " + "r" * 40)[0], 503)
        self.assertEqual(self.api.patch_count, count)
        self.now = 121
        with self.assertRaises(b.AdmissionError):
            self.req("s", "settle", "resolve_publication", {"intent": key})
        self.observed = HEAD_CODE
        self.api.lose_response = True
        result = self.req("s", "settle", "resolve_publication", {"intent": key})
        self.assertTrue(result["replayed"])
        self.reopen()
        latest = self.store.read_hot()
        self.assertIsNone(latest.manifest["pending_intent"])
        self.assertEqual(latest.state["tasks"]["a"]["status"], "OPEN")
        self.assertEqual(self.store.hot_publication_at(latest, key)["resolution"],
                         {"operation": result["operation"], "observed_head": HEAD_CODE})
        self.assertIsNone(self.store.hot_publication_at(pinned, key)["resolution"])
        replay = self.req("a", "artifact", "accept_artifact", proposal)
        self.assertTrue(replay["replayed"])
        self.assertFalse(replay["source_promoted"])
        self.assertEqual(replay["artifact"], accepted["artifact"])
        self.assertFalse(self.req("a", "claim", "acquire")["lease"]["active"])
        page = self.store.hot_task_history(latest, "a", limit=50)
        kinds = [row["kind"] for row in page["events"]]
        for kind in ("artifact_accepted", "publication_intent", "publication_resolved", "expired"):
            self.assertEqual(kinds.count(kind), 1)
        self.assertEqual(endpoint.handle("GET", "/v3/projects/wii-golf/read-v2/tasks/a/history",
                                         "Bearer " + "r" * 40)[0], 200)

    def test_hot_publication_single_use_and_trusted_review(self):
        proposal, accepted, payload = self.accept()
        count = self.api.patch_count
        with self.assertRaises(b.AdmissionError):
            self.req("b", "stolen", "prepare_publication", payload)
        with self.assertRaises(b.AdmissionError):
            self.req("a", "main", "prepare_publication", {**payload, "target": "main"})
        self.allow = False
        with self.assertRaises(b.AdmissionError):
            self.req("a", "denied", "prepare_publication", payload)
        self.assertEqual(self.api.patch_count, count)
        self.allow = True
        intent = self.req("a", "prepare", "prepare_publication", payload)
        self.observed = BASE_CODE
        self.req("s", "resolve", "resolve_publication", {"intent": intent["operation"]})
        self.reopen()
        count = self.api.patch_count
        with self.assertRaises(storage.StoreError):
            self.req("a", "retry", "prepare_publication", payload)
        self.assertEqual(self.api.patch_count, count)
        self.assertFalse(self.req("a", "prepare", "prepare_publication", payload)["source_promoted"])

    def test_settled_full_journal_migrates_with_exact_history_and_replay(self):
        api = FakeGit()
        full_store = storage.GitHubStore(api, "owner/repo", BRANCH)
        full_store.bootstrap_test(BASE, initial(), "seed")
        self.store = full_store
        self.broker = b.Broker(full_store, self.credentials, clock=lambda: self.now,
                               reviewer=lambda *args: True, inspector=self.inspector,
                               publication_observer=lambda *args: BASE_CODE)
        proposal, accepted, payload = self.accept()
        intent = self.req("a", "prepare", "prepare_publication", payload)
        pending = full_store.read()
        patches = api.patch_count
        with self.assertRaisesRegex(storage.StoreError, "unresolved publication"):
            full_store.initialize_hot(pending, "hot-convert")
        self.assertEqual(api.patch_count, patches)
        settled = self.req("s", "settle", "resolve_publication",
                           {"intent": intent["operation"]})
        self.now = 121
        self.req("s", "expire", "sweep")
        source = full_store.read()
        expected_events = full_store.task_history("a", limit=50)["events"]
        full_store.initialize_hot(source, "hot-convert")
        self.api = api
        self.reopen()
        snap = self.store.read_hot()
        self.assertEqual(self.store.hot_lookup("artifact", accepted["operation"]),
                         accepted["artifact"])
        self.assertEqual(self.store.hot_publication_at(snap, intent["operation"]),
                         source.envelope["publications"][intent["operation"]])
        self.assertEqual(self.store.hot_lookup("receipt", settled["operation"]),
                         source.envelope["receipts"][settled["operation"]])
        events = self.store.hot_task_history(snap, "a", limit=50)["events"]
        self.assertEqual(sorted((x["revision"], x["kind"], x["commit"]) for x in expected_events),
                         sorted((x["revision"], x["kind"], x["source_commit"]) for x in events))
        count = api.patch_count
        self.assertEqual(self.req("a", "artifact", "accept_artifact", proposal)["artifact"],
                         accepted["artifact"])
        self.assertTrue(self.req("a", "prepare", "prepare_publication", payload)["replayed"])
        self.assertTrue(self.req("s", "settle", "resolve_publication",
                                 {"intent": intent["operation"]})["replayed"])
        self.assertEqual(api.patch_count, count)

    def test_read_v3_shows_freeze_and_actual_root_capacity_without_mutation(self):
        import json
        _, _, payload = self.accept()
        key = self.req("a", "prepare", "prepare_publication", payload)["operation"]
        endpoint = b.OperatorReadEndpoint("wii-golf", self.broker)
        prefix = "/v3/projects/wii-golf/read-v3"
        auth = "Bearer " + "r" * 40
        patches = self.api.patch_count
        snap = self.store.read_hot()
        self.now = 121
        code, _, body = endpoint.handle("GET", prefix + "/status", auth)
        self.assertEqual(code, 200)
        view = json.loads(body)
        self.assertEqual(view["wire_version"], 3)
        self.assertTrue(view["publication_supported"])
        self.assertTrue(view["queue_frozen"])
        self.assertEqual(view["publication_pending"], key)
        self.assertEqual(view["publications"], {key: {"resolution": None}})
        self.assertEqual(view["eligible"], [])
        code, _, body = endpoint.handle("GET", prefix + "/capacity", auth)
        self.assertEqual(code, 200)
        capacity = json.loads(body)
        self.assertEqual(capacity["head"], snap.head)
        self.assertEqual(capacity["used_bytes"], snap.root_bytes)
        self.assertEqual(capacity["remaining_bytes"], storage.MAX_LEDGER - snap.root_bytes)
        self.assertEqual(capacity["capacity_scope"], "hot_root_only")
        self.assertTrue(capacity["publication_pending"])
        self.assertEqual(capacity["receipt_count"], snap.state["revision"] + 1)
        self.assertEqual(capacity["active_run_count"], len(snap.state["runs"]))
        self.assertEqual(capacity["archived_run_count"], sum(snap.state["archived_fences"].values()))
        code, _, body = endpoint.handle("GET", prefix + "/tasks/a/history", auth)
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["wire_version"], 3)
        self.assertEqual(self.api.patch_count, patches)
        self.observed = BASE_CODE
        self.req("s", "settle", "resolve_publication", {"intent": key})
        code, _, body = endpoint.handle("GET", prefix + "/status", auth)
        self.assertEqual(code, 200)
        self.assertFalse(json.loads(body)["queue_frozen"])
        self.assertIsNone(json.loads(body)["publication_pending"])

    def test_hot_manifest_reserves_settlement_headroom(self):
        _, _, payload = self.accept()
        snap = self.store.read_hot()
        used = len(storage.canonical(snap.manifest))
        count = self.api.patch_count
        with patch.object(storage, "MAX_LEDGER", used + 1024):
            with self.assertRaisesRegex(storage.StoreError, "hot settlement reserve"):
                self.req("a", "prepare", "prepare_publication", payload)
        self.assertEqual(self.store.read_hot(), snap)
        self.assertEqual(self.api.patch_count, count)



class IsolatedPublicationTransportTests(unittest.TestCase):
    def setUp(self):
        import shutil
        self.git = shutil.which("git")
        self.assertIsNotNone(self.git, "Git required for isolated publication regression")
        self.git = str(Path(self.git).absolute())
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).absolute()
        work = self.root / "fixture"
        self.scratch = self.root / "scratch"
        self.scratch.mkdir()
        self.real_run = subprocess.run

        def git(*args, data=None):
            return self.real_run([self.git, *map(str, args)], cwd=self.root,
                input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                check=True).stdout
        git("init", "-q", work)
        def commit(message):
            git("-C", work, "-c", "user.name=Fixture", "-c",
                "user.email=fixture@example.invalid", "commit", "-q",
                "--allow-empty", "-m", message)
            return git("-C", work, "rev-parse", "HEAD").decode().strip()
        self.base = commit("base")
        self.head = commit("child")
        self.grandchild = commit("grandchild")
        self.pack = git("-C", work, "pack-objects", "--stdout", "--revs",
                        data=(self.grandchild + "\n").encode("ascii"))
        self.target = "orchestration/v3-publication-test-unit"
        self.command = g.PublicationCommand("owner/repo", BRANCH, BASE,
            "dispatch-test", self.target, self.base, self.head, "a" * 64)
        self.token = "synthetic_token_not_a_real_credential"
        self.calls = []
        self.token_reads = 0

    def credential(self):
        self.token_reads += 1
        return self.token

    def transport(self, pack=None):
        return g.IsolatedGitHubPublicationTransport(
            "owner/repo", BRANCH, self.target, self.git, self.scratch,
            lambda command: self.pack if pack is None else pack, self.credential)

    def intercept(self, *args, **kwargs):
        argv = args[0]
        env = dict(kwargs["env"])
        self.calls.append((list(argv), env))
        if "push" in argv:
            return subprocess.CompletedProcess(argv, 0)
        return self.real_run(*args, **kwargs)

    def test_actual_pack_isolation_and_fixed_https_argv(self):
        import base64
        import os
        injected = {"GIT_CONFIG_COUNT": "99", "GIT_TRACE": "1",
                    "HTTPS_PROXY": "https://untrusted.invalid",
                    "GIT_OBJECT_DIRECTORY": "untrusted",
                    "GIT_ASKPASS": "untrusted", "HOST_SECRET": "untrusted"}
        with patch.dict(os.environ, injected), patch.object(
                g.subprocess, "run", side_effect=self.intercept):
            self.assertIs(self.transport()(self.command), True)
        self.assertEqual(self.token_reads, 1)
        self.assertEqual(len(self.calls), 5)
        for argv, env in self.calls:
            self.assertNotIn(self.token, " ".join(argv))
            for key in injected:
                if key != "GIT_CONFIG_COUNT":
                    self.assertNotIn(key, env)
            self.assertEqual(env["GIT_CONFIG_NOSYSTEM"], "1")
            self.assertEqual(env["GIT_ALLOW_PROTOCOL"], "https")
        for _, env in self.calls[:-1]:
            self.assertNotIn("GIT_CONFIG_COUNT", env)
            self.assertNotIn("GIT_CONFIG_VALUE_0", env)
        argv, env = self.calls[-1]
        self.assertEqual(argv[-len(g.exact_push_arguments(self.command)):],
                         g.exact_push_arguments(self.command))
        self.assertIn("http.followRedirects=false", argv)
        self.assertIn("http.sslVerify=true", argv)
        self.assertIn("credential.helper=", argv)
        self.assertEqual(env["GIT_CONFIG_COUNT"], "1")
        self.assertEqual(base64.b64decode(
            env["GIT_CONFIG_VALUE_0"].split()[-1]).decode(),
            "x-access-token:" + self.token)
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_invalid_pack_parent_scope_and_token_never_push(self):
        from dataclasses import replace
        with patch.object(g.subprocess, "run", side_effect=self.intercept):
            for command, pack in (
                (replace(self.command, target="orchestration/v3-publication-test-other"), self.pack),
                (self.command, b"not a pack"),
                (self.command, b"PACK" + b"x" * 32),
                (replace(self.command, head=self.grandchild), self.pack),
            ):
                with self.assertRaises(g.ArtifactError):
                    self.transport(pack)(command)
            self.assertEqual(self.token_reads, 0)
            self.token = "invalid token\n"
            with self.assertRaises(g.ArtifactError):
                self.transport()(self.command)
        self.assertEqual(self.token_reads, 1)
        self.assertFalse(any("push" in argv for argv, _ in self.calls))
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_push_timeout_is_not_retried_or_exposed(self):
        def timeout(*args, **kwargs):
            if "push" in args[0]:
                self.calls.append((args[0], {}))
                raise subprocess.TimeoutExpired(self.token, 1)
            return self.intercept(*args, **kwargs)
        with patch.object(g.subprocess, "run", side_effect=timeout):
            with self.assertRaisesRegex(g.ArtifactError,
                    "^isolated publication outcome unconfirmed$"):
                self.transport()(self.command)
        self.assertEqual(sum("push" in argv for argv, _ in self.calls), 1)
        self.assertEqual(list(self.scratch.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
