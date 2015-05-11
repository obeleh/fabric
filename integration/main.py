from spec import skip, Spec, ok_, eq_

from fabric.connection import Connection


class Main(Spec):
    def connection_open_generates_real_connection(self):
        c = Connection('localhost')
        c.open()
        eq_(c.client.get_transport().active, True)
        eq_(c.is_connected, True)
        return c

    def connection_close_closes_connection(self):
        c = self.connection_open_generates_real_connection()
        c.close()
        eq_(c.client.get_transport(), None)
        eq_(c.is_connected, False)

    def simple_command_on_host(self):
        """
        Run command on host "localhost"
        """
        result = Connection('localhost').run('echo foo', hide=True)
        eq_(result.stdout, "foo\n")
        eq_(result.exited, 0)
        eq_(result.ok, True)

    def simple_command_on_multiple_hosts(self):
        """
        Run command on localhost...twice!
        """
        skip()
        Batch(['localhost', 'localhost']).run('echo foo')
        # => [Result, Result

    def sudo_command(self):
        """
        Run command via sudo on host "localhost"
        """
        skip()
        Connection('localhost').sudo('echo foo')

    def mixed_sudo_and_normal_commands(self):
        """
        Run command via sudo, and not via sudo, on "localhost"
        """
        skip()
        cxn = Connection('localhost')
        cxn.run('whoami')
        cxn.sudo('whoami')
        # Alternately...
        cxn.run('whoami', runner=Basic)
        cxn.run('whoami', runner=Sudo)

    def switch_command_between_local_and_remote(self):
        """
        Run command truly locally, and over SSH via "localhost"
        """
        # TODO: Only really makes sense at the task level though...
        skip()
        # Basic/raw
        run('hostname') # Or Context().run('hostname')
        Connection('localhost').run('hostname')