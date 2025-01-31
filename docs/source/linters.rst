.. _linters:

Linters
=======

``ensure_timestamps (L001)``
---------------------

Ensure that a job is configured to produce timestamps in its console
output.

``ensure_workspace_cleanup (L002)``
----------------------------

Ensure that a job is configured to clean the workspace prior to execution.

Configuration Options
~~~~~~~~~~~~~~~~~~~~~

No configuration options.

``check_env_inject (L003)``
--------------------

If required environment settings are configured (see below), ensure
that all jobs have an inject property with a properties-content that
contain those environment settings.  By default, this will run, but
will always skip if no requirements are specified.

Configuration Options
~~~~~~~~~~~~~~~~~~~~~

``required_configuration_settings``
    A comma-separated list of environment variable setting lines that
    should be present in job environments.

``check_for_empty_shell (L006)``
-------------------------

Ensure that all shell builders in a job have some content.

Configuration Options
~~~~~~~~~~~~~~~~~~~~~

No configuration options.

``check_job_references (L004)``
------------------------

Ensure that all job references have a target within the generated
Jenkins configuration.  Currently, this checks the ``trigger-builds``
builder.

``check_column_configuration (L005)``
------------------------

Ensure that each list view has at least one column configured.

Configuration Options
~~~~~~~~~~~~~~~~~~~~~

No configuration options.

``check_shebang (L007)``
-----------------

Ensure that all shell builders in a job have an appropriate shebang.

This will ignore non-shell shebangs, and ensure that any shell shebangs
have all of `-eux` set.  The Jenkins default shebang is accepted, but
this can be configured (see below).

Configuration Options
~~~~~~~~~~~~~~~~~~~~~

``allow_default_shebang``
    A boolean defining whether the default Jenkins shebang should be
    permitted in shell builders (i.e. should shell builders be
    permitted to have no shebang).  Defaults to True.

``required_shell_options``
    A string of the shell options that are required to be present in
    the shebang of shell builders.  Defaults to "eux".
