import errno
from os.path import join, expanduser

from fabric.config import Config
from paramiko.config import SSHConfig

from mock import patch, call
from spec import Spec, eq_, ok_

from _util import support_path


class Config_(Spec):
    def defaults_to_merger_of_global_defaults(self):
        # I.e. our global_defaults + Invoke's global_defaults
        c = Config()
        # From invoke's global_defaults
        eq_(c.run.warn, False)
        # From ours
        eq_(c.port, 22)

    def has_various_Fabric_specific_default_keys(self):
        # NOTE: Duplicates some other tests but we're now starting to
        # grow options not directly related to user/port stuff, so best
        # to have at least one test listing all expected keys.
        for keyparts in (
            ('port',),
            ('user',),
            ('forward_agent',),
            ('sudo', 'prompt'),
            ('sudo', 'password'),
        ):
            obj = Config()
            for key in keyparts:
                err = "Didn't find expected config key path '{0}'!"
                assert key in obj, err.format(".".join(keyparts))
                obj = obj[key]

    def our_defaults_override_invokes(self):
        "our defaults override invoke's"
        with patch.object(
            Config,
            'global_defaults',
            return_value={
                'run': {'warn': "nope lol"},
                'user': 'me',
                'port': 22,
                'forward_agent': False,
            }
        ):
            # If our global_defaults didn't win, this would still
            # resolve to False.
            eq_(Config().run.warn, "nope lol")

    def we_override_replace_env(self):
        # This value defaults to False in Invoke proper.
        eq_(Config().run.replace_env, True)

    class ssh_config:
        system_path = join(support_path, 'ssh_config', 'system.conf')
        user_path = join(support_path, 'ssh_config', 'user.conf')
        runtime_path = join(support_path, 'ssh_config', 'runtime.conf')
        empty_kwargs = dict(
            system_ssh_path='nope/nope/nope',
            user_ssh_path='nope/noway/nuhuh',
        )

        def defaults_to_empty_sshconfig_obj_if_no_files_found(self):
            c = Config(**self.empty_kwargs)
            # TODO: Currently no great public API that lets us figure out if
            # one of these is 'empty' or not. So for now, expect an empty inner
            # SSHConfig._config from an un-.parse()d such object. (AFAIK, such
            # objects work fine re: .lookup, .get_hostnames etc.)
            ok_(type(c.base_ssh_config) is SSHConfig)
            eq_(c.base_ssh_config._config, [])

        def object_can_be_given_explicitly_via_ssh_config_kwarg(self):
            sc = SSHConfig()
            ok_(Config(ssh_config=sc).base_ssh_config is sc)

        @patch.object(Config, '_load_ssh_file')
        def when_config_obj_given_default_paths_are_not_sought(self, method):
            sc = SSHConfig()
            Config(ssh_config=sc)
            ok_(not method.called)

        @patch.object(Config, '_load_ssh_file')
        def config_obj_prevents_loading_runtime_path_too(self, method):
            sc = SSHConfig()
            Config(ssh_config=sc, runtime_ssh_path=self.system_path)
            ok_(not method.called)

        @patch.object(Config, '_load_ssh_file')
        def when_runtime_path_given_other_paths_are_not_sought(self, method):
            Config(runtime_ssh_path=self.runtime_path)
            method.assert_called_once_with(self.runtime_path)

        def runtime_path_does_not_die_silently(self):
            try:
                Config(runtime_ssh_path='sure/thing/boss/whatever/you/say')
            except IOError as e:
                ok_("No such file or directory" in str(e))
                eq_(e.errno, errno.ENOENT)
            else:
                assert False, "Bad runtime path didn't raise IOError!"

        # TODO: skip on windows
        @patch.object(Config, '_load_ssh_file')
        def default_file_paths_match_openssh(self, method):
            Config()
            method.assert_has_calls([
                call(expanduser('~/.ssh/config')),
                call('/etc/ssh/ssh_config'),
            ])

        def system_path_loads_ok(self):
            c = Config(**dict(
                self.empty_kwargs,
                system_ssh_path=self.system_path,
            ))
            eq_(
                c.base_ssh_config.get_hostnames(),
                set(['system', 'shared', '*']),
            )

        def user_path_loads_ok(self):
            c = Config(**dict(
                self.empty_kwargs,
                user_ssh_path=self.user_path,
            ))
            eq_(
                c.base_ssh_config.get_hostnames(),
                set(['user', 'shared', '*']),
            )

        def both_paths_loaded_if_both_exist_with_user_winning(self):
            c = Config(
                user_ssh_path=self.user_path,
                system_ssh_path=self.system_path,
            )
            eq_(
                c.base_ssh_config.get_hostnames(),
                set(['user', 'system', 'shared', '*']),
            )
            # Expect the user value (321), not the system one (123)
            eq_(c.base_ssh_config.lookup('shared')['port'], '321')

        @patch.object(Config, '_load_ssh_file')
        @patch('fabric.config.os.path.exists', lambda x: True)
        def runtime_path_subject_to_user_expansion(self, method):
            # TODO: other expansion types? no real need for abspath...
            tilded = '~/probably/not/real/tho'
            Config(runtime_ssh_path=tilded)
            method.assert_called_once_with(expanduser(tilded))

        @patch.object(Config, '_load_ssh_file')
        def user_path_subject_to_user_expansion(self, method):
            # TODO: other expansion types? no real need for abspath...
            tilded = '~/probably/not/real/tho'
            Config(user_ssh_path=tilded)
            method.assert_any_call(expanduser(tilded))

        class core_ssh_load_option_allows_skipping_ssh_config_loading:
            @patch.object(Config, '_load_ssh_file')
            def skips_default_paths(self, method):
                Config(overrides={'load_ssh_configs': False})
                ok_(not method.called)

            @patch.object(Config, '_load_ssh_file')
            def does_not_affect_explicit_object(self, method):
                sc = SSHConfig()
                c = Config(
                    ssh_config=sc,
                    overrides={'load_ssh_configs': False},
                )
                # Implicit loading still doesn't happen...sanity check
                ok_(not method.called)
                # Real test: the obj we passed in is present as usual
                ok_(c.base_ssh_config is sc)

            @patch.object(Config, '_load_ssh_file')
            def does_not_skip_loading_runtime_path(self, method):
                Config(
                    runtime_ssh_path=self.runtime_path,
                    overrides={'load_ssh_configs': False},
                )
                # Expect that loader method did still run (and, as usual, that
                # it did not load any other files)
                method.assert_called_once_with(self.runtime_path)