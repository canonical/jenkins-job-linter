#!/usr/bin/env python3
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
"""Run a series of checks against compiled job XML."""
import os
import sys
from configparser import ConfigParser
from typing import Optional
from xml.etree import ElementTree

import click
import jenkins

from jenkins_job_linter.config import _filter_config, GetListConfigParser
from jenkins_job_linter.linters import LINTERS, LINTER_SHORT_CODES
from jenkins_job_linter.models import LintContext, RunContext


def lint_job_xml(ctx: RunContext, job_name: str, tree: ElementTree.ElementTree,
                 config: GetListConfigParser) -> bool:
    """Run all the linters against an XML tree."""
    success = True
    for linter_name, linter in LINTERS.items():
        if linter_name in config.getlist('job_linter', 'disable_linters'):
            continue
        only_run = config.getlist('job_linter', 'only_run')
        if only_run and linter_name not in only_run:
            continue
        section = config['job_linter:{}'.format(linter_name)]
        result, text = linter(LintContext(section, ctx, tree)).check()
        if not result.value:
            success = False
            output = '{}: ({}) {}: FAIL'.format(job_name, linter.short_code,
                                                linter.description)
            if text is not None:
                output += ': {}'.format(text)
            print(output)
    return success


def lint_jobs_from_directory(compiled_job_directory: str,
                             config: ConfigParser) -> bool:
    """Load jobs from a directory and run linters against each one."""
    config = _filter_config(config)
    success = True
    filenames = os.listdir(compiled_job_directory)
    for job_file in filenames:
        job_path = os.path.join(compiled_job_directory, job_file)
        result = lint_job_xml(RunContext(filenames), job_file,
                              ElementTree.parse(job_path), config)
        success = success and result
    return success


def lint_jobs_from_running_jenkins(jenkins_url: str, jenkins_username: str,
                                   jenkins_password: str,
                                   config: ConfigParser) -> bool:
    """Load jobs from a running Jenkins and run linters against each one."""
    config = _filter_config(config)
    server = jenkins.Jenkins(
        jenkins_url, username=jenkins_username, password=jenkins_password)
    success = True
    job_names = [j['name'] for j in server.get_jobs()]
    for job_name in job_names:
        job_xml = server.get_job_config(job_name)
        element_tree = ElementTree.ElementTree(ElementTree.fromstring(job_xml))
        result = lint_job_xml(RunContext(job_names), job_name,
                              element_tree, config)
        success = success and result
    return success


@click.group()
@click.option('--conf', type=click.Path(exists=True, dir_okay=False))
@click.option('--select', default=[], metavar='<lint_short_code>',
              type=click.STRING,
              help='Select which linters, by short code, to run. '
                   'A comma separated list is accepted'
                   'If conf option is used then --select is not used.'
                   'Use `list-linters` sub command to view list')
@click.option('--ignore', default=[], metavar='<lint_short_code>',
              type=click.STRING,
              help='Select which linters, by short code, to ignore. '
                   'A comma separated list is accepted'
                   'If conf option is used then --ignore is not used'
                   'Use `list-linters` sub command to view list')
@click.pass_context
def main(ctx: click.Context, conf: Optional[str] = None,
         select: Optional[str] = None,
         ignore: Optional[str] = None) -> None:
    """jenkins-job-linter: check your Jenkins jobs for common errors."""
    config = ConfigParser()
    if conf is not None:
        config.read(conf)
    else:
        if select:
            config.add_section('job_linter')
            only_run = []
            for linter_short_code in select.split(','):
                if linter_short_code in LINTER_SHORT_CODES:
                    only_run.append(LINTER_SHORT_CODES[linter_short_code])

            config.set('job_linter', 'only_run', ','.join(only_run))
        if ignore:
            config.add_section('job_linter')
            disable_linters = []
            for linter_short_code in ignore.split(','):
                if linter_short_code in LINTER_SHORT_CODES:
                    disable_linters.append(
                            LINTER_SHORT_CODES[linter_short_code])

            config.set('job_linter', 'disable_linters',
                       ','.join(disable_linters))

    ctx.obj = config


@main.command(name='list-linters')
@click.pass_context
def list_linters(ctx: click.Context) -> None:
    """List linters."""
    for linter_name, linter in LINTERS.items():
        print('* {}'.format(linter_name))
        print('\tShort code:\n\t\t{}'.format(linter.short_code))
        print('\tDescription:\n\t\t{}'.format(linter.description))
        if linter.default_config:
            print('\tDefault Config:\n\t\t{}'.format(linter.default_config))


@main.command(name='lint-directory')
@click.argument('compiled_job_directory',
                type=click.Path(exists=True, file_okay=False))
@click.pass_context
def lint_directory(ctx: click.Context, compiled_job_directory: str) -> None:
    """Take a directory of Jenkins job XML and run some checks against it."""
    result = lint_jobs_from_directory(compiled_job_directory, ctx.obj)
    if not result:
        sys.exit(1)
    sys.exit(0)


@main.command(name='lint-jenkins')
@click.option('--jenkins-url', required=True)
@click.option('--jenkins-username', required=True)
@click.option('--jenkins-password', required=True)
@click.pass_context
def lint_jenkins(ctx: click.Context, jenkins_url: str, jenkins_username: str,
                 jenkins_password: str) -> None:
    """Lint all the jobs in a running Jenkins."""
    result = lint_jobs_from_running_jenkins(jenkins_url, jenkins_username,
                                            jenkins_password, ctx.obj)
    if not result:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()  # pragma: nocover
