"""Sanity test using rstcheck."""
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os

from lib.sanity import (
    SanitySingleVersion,
    SanityMessage,
    SanityFailure,
    SanitySuccess,
    SanitySkipped,
)

from lib.util import (
    SubprocessError,
    parse_to_list_of_dict,
    read_lines_without_comments,
    ANSIBLE_ROOT,
    find_python,
)

from lib.util_common import (
    run_command,
)

from lib.config import (
    SanityConfig,
)


class RstcheckTest(SanitySingleVersion):
    """Sanity test using rstcheck."""
    def test(self, args, targets, python_version):
        """
        :type args: SanityConfig
        :type targets: SanityTargets
        :type python_version: str
        :rtype: TestResult
        """
        ignore_file = os.path.join(ANSIBLE_ROOT, 'test/sanity/rstcheck/ignore-substitutions.txt')
        ignore_substitutions = sorted(set(read_lines_without_comments(ignore_file, remove_blank_lines=True)))

        settings = self.load_processor(args)

        paths = sorted(i.path for i in targets.include if os.path.splitext(i.path)[1] in ('.rst',))
        paths = settings.filter_skipped_paths(paths)

        if not paths:
            return SanitySkipped(self.name)

        cmd = [
            find_python(python_version),
            '-m', 'rstcheck',
            '--report', 'warning',
            '--ignore-substitutions', ','.join(ignore_substitutions),
        ] + paths

        try:
            stdout, stderr = run_command(args, cmd, capture=True)
            status = 0
        except SubprocessError as ex:
            stdout = ex.stdout
            stderr = ex.stderr
            status = ex.status

        if stdout:
            raise SubprocessError(cmd=cmd, status=status, stderr=stderr, stdout=stdout)

        if args.explain:
            return SanitySuccess(self.name)

        pattern = r'^(?P<path>[^:]*):(?P<line>[0-9]+): \((?P<level>INFO|WARNING|ERROR|SEVERE)/[0-4]\) (?P<message>.*)$'

        results = parse_to_list_of_dict(pattern, stderr)

        results = [SanityMessage(
            message=r['message'],
            path=r['path'],
            line=int(r['line']),
            column=0,
            level=r['level'],
        ) for r in results]

        settings.process_errors(results, paths)

        if results:
            return SanityFailure(self.name, messages=results)

        return SanitySuccess(self.name)
