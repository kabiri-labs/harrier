"""Content-safety and supply-chain properties of the repository itself."""

import re
import unittest

from tests.support import REPO_ROOT


class TheLoaderNeverExecutesDocumentContent(unittest.TestCase):
    """The catalogue is contributor-submitted YAML. Full loading would let a
    document construct arbitrary Python objects at parse time, making the
    repository a code-execution channel into contributors' machines and CI."""

    def test_no_call_site_can_reach_an_unsafe_loader(self):
        # Asserted against the resolved loader rather than the spelling of the
        # call, because both a safe_load and a load(Loader=SafeLoader) are safe
        # and only one of them is greppable.
        import yaml

        from pentest_navgrid import SAFE_LOADER

        self.assertTrue(
            issubclass(SAFE_LOADER, yaml.SafeLoader)
            or SAFE_LOADER.__name__ == "CSafeLoader",
            f"{SAFE_LOADER!r} is not a safe loader",
        )
        self.assertNotIsInstance(SAFE_LOADER(""), yaml.UnsafeLoader)

    def test_the_package_names_no_other_loader(self):
        allowed = ("SAFE_LOADER", "SafeLoader", "CSafeLoader", "safe_load")
        for path in (REPO_ROOT / "pentest_navgrid").rglob("*.py"):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "Loader" not in line and "yaml." not in line:
                    continue
                if line.lstrip().startswith("#") or "yaml." not in line:
                    continue
                if any(token in line for token in allowed):
                    continue
                with self.subTest(path=path.name, line=number):
                    self.assertNotIn(
                        "load", line, f"{path.name}:{number} loads YAML unsafely"
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
