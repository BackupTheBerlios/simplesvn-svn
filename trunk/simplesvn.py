#! /usr/bin/env python
# -*- coding: utf-8 -*-

## Subversion Repository creation tool
## for SUSE Linux 10.0 or later  using mod_dav_svn , mod_authz_svn and mod_auth_digest
## Author :Cristian Rodriguez R.
## License : BSD License

from optparse import OptionParser
from pwd import getpwnam
from grp import getgrnam
from os import chmod , sep , walk , lchown
from os.path import exists , join
from subprocess import call
import md5
from svn import core, repos , fs
from getpass import getpass
from string import Template

cli_parser = OptionParser(usage = "usage: %prog [-n repo] [ -t type ] [-u username]")

cli_parser.set_defaults(filesystem="fsfs", location="/srv/svn/repos/" , configdir="/etc/apache2/conf.d/", authdir="/srv/svn/user_access/", apache_user="wwwrun" , apache_group="www")

cli_parser.add_option("-n", "--name" , type="string", dest="repo" ,help="create repository REPO")
cli_parser.add_option("-f", "--fs-type" , type="string",dest="filesystem"
,help="Filesystem (default and recommended: fsfs)")
cli_parser.add_option("-l", "--location" , type="string" , dest="location" , help="Repository location (default: /srv/svn/repos/)")
cli_parser.add_option("-d", "--configdir", type="string" , dest="configdir", help="Apache configuration files location (default: /etc/apache2/conf.d/ )")
cli_parser.add_option("-a" , "--authdir" , type="string" , dest="authdir" , help="Directory where auth information is stored (default: /srv/svn/user_access/)")
cli_parser.add_option( "--apacheuser" , type="string" , dest="apache_user" , help=" the apache username (default: wwwrun )")
cli_parser.add_option("--apachegroup" , type="string" , dest="apache_group" , help=" the apache group (default: www )")
cli_parser.add_option("-u","--username",type="string",dest="adminuser", help="The repository admin username (default:admin)")

(options, args) = cli_parser.parse_args()

apacheuid = getpwnam(options.apache_user)[2]
apachegid = getgrnam(options.apache_group)[2]

# if user don't provide the repository name
if (options.repo is None):
    cli_parser.error("You MUST tell me the repository name")
elif exists(options.location + options.repo):
    cli_parser.error("Repository already exists")
if (options.adminuser is None):
    cli_parser.error("You MUST tell me what username you want")
try :
    template = Template(file( options.configdir + 'template.subversion').read())
    parsed = template.safe_substitute(repository=options.repo, authdir=options.authdir,location=options.location )

except IOError :
    cli_parser.error( "Repository template do not exist")
else :
    try:
        config_file = file(options.configdir + options.repo + '.conf' ,'wb')
        config_file.write(parsed)
        config_file.close()
    except IOError :
        cli_parser.error( "Can't write apache configuration files")

try :
    template_auth = Template( file( options.configdir + 'svnauthz.template').read() ))
    withrepo_auth = template_auth.replace('{-repository-}', options.repo)
    witheverything_auth = withrepo_auth.replace('{-adminuser-}', options.adminuser )
    #### FIXME¡¡
    auth_parsed = template_auth.safe_substitute(repository=options.repo ,
    adminuser=username )

except IOError :
    cli_parser.error( "Repository auth template do not exist")
else :
    try:
        config_file_auth = file(options.authdir + options.repo +
        '-svnauthz','wb')
        config_file_auth.write(auth_parsed)
        config_file_auth.close()
        lchown(options.authdir + options.repo + '-svnauthz',0,apachegid)
        chmod(options.authdir + options.repo + '-svnauthz',0640)

    except IOError :
        cli_parser.error( "Can't write svnauthz files")

try :
    username = raw_input("Please enter the desired repository admin username: ")
    #password will not be printed to the stdout
    password = getpass("Please enter the desired repository admin password: ")
    ### Generate the string to enter into the htdigest file
    kd = lambda x: md5.md5(':'.join(x)).hexdigest()
    digest_data = ':'.join((username, options.repo , kd([username, options.repo , password])))
    # write the data into the auth file used by apache
    auth_file = file(options.authdir + options.repo + '-passwdfile','wb')
    auth_file.write(digest_data)
    auth_file.close()

except OSError :
    cli_parser.error( "Can't create password file")

lchown(options.authdir + options.repo + '-passwdfile',0,apachegid)
chmod(options.authdir + options.repo + '-passwdfile',0640)

try:
    # we create the repository using the <rant> undocumented</rant> swig bindings.
    # took me a while to figure how to do this.
    # thanks to folks at #subversion-dev for give me some guidelines.
    core.apr_initialize()
    pool = core.svn_pool_create(None)
    repos.svn_repos_create(options.location + options.repo, '', '', None, {
        fs.SVN_FS_CONFIG_FS_TYPE: options.filesystem }, pool)
    core.svn_pool_destroy(pool)
    core.apr_terminate()

except OSError:
    cli_parser.error( "Failed to create the repository")
else:
    for dire in ['dav','db','locks']:
        lchown(options.location + options.repo + sep + dire, apacheuid, apachegid)
        for root, dirs, files in walk(options.location + options.repo + sep + dire ):
            for name in files :
                lchown(join(root, name) , apacheuid , apachegid)
            for name in dirs:
                lchown(join(root, name), apacheuid , apachegid)

    print "Reloading apache.."
     # there is no webserver.apache.reload() function yet :-)
     # have to use a system call here..
    call(["/etc/init.d/apache2", "reload"])
    print "Basic repository setup complete ..Have a lot of Fun.. ;-)"
