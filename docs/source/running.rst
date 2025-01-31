Running jenkins-job-linter
==========================

Standalone
----------

When installed, the ``jenkins-job-linter`` script will be available on
your PATH.  Running it is as simple as::

    jenkins-job-linter lint-directory <path>

``<path>`` should be a directory containing only Jenkins job XML files
(a la the output of ``jenkins-jobs test -o <path>``) as all files in
the directory will be linted.

.. note::
    You are responsible for generating the XML that jenkins-job-linter
    will run against in standalone mode.  If you don't want to do that,
    take a look at :ref:`jenkins_jobs_lint` which will do it for you if
    you are using Jenkins Job Builder. You can also run
    ``jenkins-jobs test -o xml jenkins/jobs`` which will compile all job
    in `jenkins/jobs` directory to a directory named `xml`.

``list-linters``
---------------------
::

        jenkins-job-linter list-linters

List all linters, their descriptions, default configuration and their short
codes.


.. _jenkins_jobs_lint:

``jenkins-jobs lint``
---------------------

If you have jenkins-job-linter and Jenkins Job Builder installed
alongside one another, jenkins-job-linter installs a ``lint``
subcommand in ``jenkins-jobs``.  This takes care of generating your job
XML in a temporary directory and linting it there::

    jenkins-jobs lint <path>

The ``<path>`` you give it in this case should be the path to your YAML
job definitions (i.e. the path that you would pass to ``jenkins-jobs
update`` or ``jenkins-jobs test``).
