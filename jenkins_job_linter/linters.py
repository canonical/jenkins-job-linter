# Copyright (C) 2017  Daniel Watkins <daniel@daniel-watkins.co.uk>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""A collection of linters for Jenkins job XML."""
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple  # noqa

from stevedore.extension import ExtensionManager

from jenkins_job_linter.models import LintContext


class LintResult(Enum):
    """
    The result of a linting check (i.e. pass/fail/skip).

    The value of each element represents whether or not the result should be
    considered a success when reducing down to just pass/fail.
    """

    PASS = True
    FAIL = False
    SKIP = True


LintCheckResult = Tuple[LintResult, Optional[str]]


class Linter:
    """A super-class capturing the common linting pattern."""

    default_config = {}  # type: Dict[str, Any]
    short_code = None  # type: bool

    def __init__(self, ctx: LintContext) -> None:
        """
        Create an instance of a Linter.

        :param ctx:
            A LintContext which the linter should operate against.
        """
        self._ctx = ctx

    def actual_check(self) -> LintCheckResult:
        """Perform the actual linting check."""
        raise NotImplementedError  # pragma: nocover

    def check(self) -> LintCheckResult:
        """Check the root tag of the object and call actual_check."""
        if self._ctx.tree.getroot().tag != self.root_tag:
            return LintResult.SKIP, None
        return self.actual_check()

    @property
    def description(self) -> str:
        """Output-friendly description of what this Linter does."""
        raise NotImplementedError  # pragma: nocover

    @property
    def root_tag(self) -> str:
        """XML tag name that this linter operates against."""
        raise NotImplementedError  # pragma: nocover


class JobLinter(Linter):
    """A Linter that should operate against Jenkins job objects."""

    root_tag = 'project'


class ListViewLinter(Linter):
    """A Linter that should operate against Jenkins list view objects."""

    root_tag = 'hudson.model.ListView'


class EnsureTimestamps(JobLinter):
    """Ensure that a job is configured with timestamp output."""

    short_code = 'L001'
    description = 'checking for timestamps'
    _xpath = (
        './buildWrappers/hudson.plugins.timestamper.TimestamperBuildWrapper')

    def actual_check(self) -> LintCheckResult:
        """Check that the TimestamperBuildWrapper element is present."""
        result = LintResult.FAIL
        if self._ctx.tree.find(self._xpath) is not None:
            result = LintResult.PASS
        return result, None


class EnsureWorkspaceCleanup(JobLinter):
    """Ensure that a job workspace is cleaned before execution."""

    short_code = 'L002'
    description = 'checking for workspace cleanup'
    _xpath = (
        './buildWrappers/hudson.plugins.ws__cleanup.PreBuildCleanup')

    def actual_check(self) -> LintCheckResult:
        """Check that the PreBuildCleanup element is present."""
        result = LintResult.FAIL
        if self._ctx.tree.find(self._xpath) is not None:
            result = LintResult.PASS
        return result, None


class CheckEnvInject(JobLinter):
    """Ensure that required environment variables are injected."""

    short_code = 'L003'
    default_config = {
        'required_environment_settings': '',
    }

    description = 'checking environment variable injection'
    _xpath = './properties/EnvInjectJobProperty/info/propertiesContent'

    def _check_properties(
            self, properties_content: str,
            required_environment_settings: List[str]) -> LintCheckResult:
        """
        Check that properties are correctly configured.

        This assumes that sanity checking of the parameters has already
        happened.
        """
        configured_properties = properties_content.split('\n')
        for required_setting in required_environment_settings:
            if required_setting not in configured_properties:
                return LintResult.FAIL, 'Did not find {}'.format(
                    required_setting)
        return LintResult.PASS, None

    def actual_check(self) -> LintCheckResult:
        """Check that configured lines are present in propertiesContent."""
        required_environment_settings = self._ctx.config.getlist(
            'required_environment_settings')
        if not required_environment_settings:
            return LintResult.SKIP, None
        properties_content = self._ctx.tree.find(self._xpath)
        if properties_content is None:
            return LintResult.FAIL, 'Injection unexpectedly unconfigured'
        if properties_content.text is None:  # pragma: nocover
            # Integration tests can't produce input that fails this way, so we
            # can't get test coverage
            return LintResult.FAIL, 'Injected properties empty'
        return self._check_properties(properties_content.text,
                                      required_environment_settings)


class CheckJobReferences(JobLinter):
    """Ensure that jobs referenced for triggering exist."""

    short_code = 'L004'
    description = 'checking job references'
    _xpath = (
        './builders/hudson.plugins.parameterizedtrigger.TriggerBuilder/configs'
        '/*/projects')

    def actual_check(self) -> LintCheckResult:
        """Check referenced jobs against RunContext.object_names."""
        project_nodes = self._ctx.tree.findall(self._xpath)
        for node in project_nodes:
            projects = node.text
            if projects is None:
                return LintResult.FAIL, 'No reference configured'
            for project in projects.split(','):
                project = project.strip()
                if project not in self._ctx.run_ctx.object_names:
                    return (LintResult.FAIL,
                            'Reference to missing object {}'.format(project))
        return LintResult.PASS, None


class CheckColumnConfiguration(ListViewLinter):
    """Ensure that each list view has at least one column configured."""

    short_code = 'L005'
    description = 'checking column configuration'
    _xpath = './columns/*'

    def actual_check(self) -> LintCheckResult:
        """Check that there are some column nodes configured."""
        column_nodes = self._ctx.tree.findall(self._xpath)
        if column_nodes is None or len(column_nodes) == 0:
            return LintResult.FAIL, 'No columns configured'
        return LintResult.PASS, None


class ShellBuilderLinter(JobLinter):
    """A linter that operates on the shell builders of jobs."""

    short_code = 'L006'
    _xpath = './builders/hudson.tasks.Shell/command'

    def actual_check(self) -> LintCheckResult:
        """
        Iterate over the shell builders in a job calling self.shell_check.

        If any of the self.shell_check calls fail, this returns that result
        immediately.  (Note also that it assumes that there will only be text
        to return on that single failure.)
        """
        shell_builders = self._ctx.tree.findall(self._xpath)
        if not shell_builders:
            return LintResult.SKIP, None
        for shell_builder in shell_builders:
            shell_script = shell_builder.text
            result, text = self.shell_check(shell_script)
            if result == LintResult.FAIL:
                return result, text
        return LintResult.PASS, None

    def shell_check(self, shell_script: Optional[str]) -> LintCheckResult:
        """Perform a check for a specific shell builder."""
        raise NotImplementedError  # pragma: nocover


class CheckForEmptyShell(ShellBuilderLinter):
    """Ensure that shell builders in a job have some content."""

    short_code = 'L006'
    description = 'checking shell builder shell scripts are not empty'

    def shell_check(self, shell_script: Optional[str]) -> Tuple[LintResult,
                                                                None]:
        """Check that a shell script is not empty."""
        if shell_script is None:
            return LintResult.FAIL, None
        return LintResult.PASS, None


class CheckShebang(ShellBuilderLinter):
    """
    Ensure that shell builders in a job have an appropriate shebang.

    Specifically, ensure that those with a shell shebang call the shell with
    -eux.

    Shell builders with no shebang or a non-shell shebang are skipped.
    """

    short_code = 'L007'
    default_config = {
        'allow_default_shebang': True,
        'required_shell_options': 'eux',
    }

    description = 'checking shebang of shell builders'

    def _check_shell_shebang(self, required_shell_options_set: Set[str],
                             first_line: str) -> bool:
        """Given a shell shebang and required options, check it."""
        line_parts = first_line.split(' ')
        if len(line_parts) < 2:
            return False
        shell_options_match = re.match(r'-([a-z]+)', line_parts[1])
        if shell_options_match is None:
            return False
        if not required_shell_options_set.issubset(
                set(shell_options_match.group(1))):
            return False
        return True

    def _handle_jenkins_default(self) -> LintCheckResult:
        """Return the appropriate result for a Jenkins-default shebang."""
        if self._ctx.config.getboolean('allow_default_shebang'):
            return LintResult.SKIP, None
        else:
            return LintResult.FAIL, "Shebang is Jenkins' default"

    def shell_check(self, shell_script: Optional[str]) -> LintCheckResult:
        """Check a shell script for an appropriate shebang."""
        if shell_script is None:
            return LintResult.SKIP, None
        first_line = shell_script.splitlines()[0]
        if not first_line.startswith('#!'):
            # This will use Jenkins' default
            return self._handle_jenkins_default()
        if re.match(r'#!/bin/[a-z]*sh', first_line) is None:
            # This has a non-shell shebang
            return LintResult.SKIP, None
        required_shell_options_set = set(
            self._ctx.config['required_shell_options'])
        if not required_shell_options_set:
            return LintResult.PASS, None
        if not self._check_shell_shebang(required_shell_options_set,
                                         first_line):
            return LintResult.FAIL, 'Shebang is {}'.format(first_line)
        return LintResult.PASS, None


extension_manager = ExtensionManager(namespace='jjl.linters')
LINTERS = {ext.name: ext.plugin for ext in extension_manager}
LINTER_SHORT_CODES = {linter.short_code: linter_name
                      for linter_name, linter in LINTERS.items()}
