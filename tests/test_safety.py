"""Content-safety and supply-chain properties of the repository itself."""

import re
import unittest

from tests.support import REPO_ROOT


class TheLoaderNeverExecutesDocumentContent(unittest.TestCase):
    def test_only_safe_load_is_used(self):
        # The catalogue is contributor-submitted YAML. Full loading would let a
        # document construct arbitrary Python objects at parse time, making the
        # repository a code-execution channel into contributors' machines and CI.
        for path in (REPO_ROOT / "harrier").rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotRegex(
                    source,
                    r"yaml\.(?!safe_load)\w*load",
                    f"{path.name} loads YAML without safe_load",
                )


class PayloadsStayAtProofOfConceptLevel(unittest.TestCase):
    DESTRUCTIVE = re.compile(
        r"\b(DROP\s+(TABLE|DATABASE|SCHEMA)|TRUNCATE\s+TABLE|"
        r"DELETE\s+FROM(?!\s+\w+\s+WHERE\s+1\s*=\s*0)|SHUTDOWN|xp_cmdshell)\b",
        re.IGNORECASE,
    )

    def test_no_payload_carries_a_destructive_operation(self):
        for path in (REPO_ROOT / "payloads").rglob("*.yaml"):
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                if not line.strip().startswith("payload:"):
                    continue
                with self.subTest(path=path.name, line=line.strip()[:60]):
                    self.assertIsNone(
                        self.DESTRUCTIVE.search(line),
                        "payloads stay at proof-of-concept level: markers, benign "
                        "metadata reads, non-destructive probes",
                    )


class NothingFromARealTargetIsCommitted(unittest.TestCase):
    """No concrete host where a placeholder belongs.

    Tool homepages in the registry are legitimate and necessary. What must never
    appear is a real host inside a payload or a command template: entries use
    {{VAR}} placeholders so they are copy-and-run, and a literal host there is
    either taken from a real engagement or an invitation to treat someone else's
    infrastructure as one.
    """

    HOST_IN_TEMPLATE = re.compile(
        r"https?://(?!\{\{|localhost|127\.0\.0\.1|example\.(?:com|org|net))[a-z0-9.-]+",
        re.IGNORECASE,
    )
    #: Fields whose value is meant to be executed or sent, as opposed to read.
    TEMPLATE_FIELDS = ("payload:", "cmd:")

    def test_no_concrete_host_appears_where_a_placeholder_belongs(self):
        for folder in ("payloads", "toolbox", "knowledge"):
            for path in (REPO_ROOT / folder).rglob("*.yaml"):
                for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if not line.strip().startswith(self.TEMPLATE_FIELDS):
                        continue
                    found = self.HOST_IN_TEMPLATE.search(line)
                    with self.subTest(path=str(path.relative_to(REPO_ROOT)), line=number):
                        self.assertIsNone(
                            found,
                            f"literal host {found.group(0) if found else ''!r} where a "
                            "placeholder belongs -- examples must be invented, never captured",
                        )

    def test_command_templates_parameterise_their_target(self):
        import yaml

        registry = yaml.safe_load((REPO_ROOT / "toolbox" / "registry.yaml").read_text("utf-8"))
        for tool in registry:
            for invocation in tool["invocations"]:
                command = invocation["cmd"]
                if "://" not in command and "{{" not in command:
                    continue
                with self.subTest(tool=tool["id"], cmd=command[:50]):
                    self.assertIn(
                        "{{",
                        command,
                        "a command carrying a target must parameterise it",
                    )


if __name__ == "__main__":
    unittest.main()
