"""Synthetic immutable artifact admission tests; no real repository writes."""
import copy
import sys
import unittest
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

if __name__ == "__main__":
    unittest.main()
