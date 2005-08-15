#! /usr/bin/env python

## Subversion Repository creation tool 
##for SuSE Linux >=9.3  using mod_dav_svn and mod_authz_svn
##Author :Cristian Rodriguez R.
##License : BSD License 

from optparse import OptionParser
from pwd import getpwnam
from grp import getgrnam
from os import chown , chmod , sep , walk , lchown
from os.path import exists , join 
from subprocess import call
#from svn import core, repos , fs # WITFM ???

cli_parser = OptionParser(usage = "usage: %prog [-n repo] [ -t type ] [-u username]")

cli_parser.set_defaults(filesystem="fsfs", location="/srv/svn/repos/" , configdir="/etc/apache2/conf.d/", authdir="/srv/svn/user_access/", apache_user="wwwrun" , apache_group="www")

cli_parser.add_option("-n", "--name" , type="string", dest="repo" ,help="create repository REPO")
cli_parser.add_option("-f", "--fs-type" , type="string",dest="filesystem" ,help="Filesystem (default: fsfs)")
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
if options.repo is None:
     cli_parser.error("You MUST tell me the repository name")
elif exists(options.location + options.repo):
	cli_parser.error("Repository already exists")
if options.adminuser is None:
    cli_parser.error("You MUST tell me what username you want")
try :
        template = open( options.configdir + 'template.subversion').read()
        withrepo = template.replace('{-repository-}', options.repo)
        withauthdir = withrepo.replace('{-authdir-}', options.authdir )
        witheverything = withauthdir.replace('{-location-}',options.location)
except IOError :
    cli_parser.error( "Repository template do not exist (RTFM)")
else :
    try:
        config_file = open(options.configdir + options.repo + '.svnrepo' ,'w')
        config_file.write(witheverything)
        config_file.close()
    except IOError :
        cli_parser.error( "Can't write apache configuration files")
    
try :
        template_auth = open( options.configdir + 'svnauthz.template').read()
        withrepo_auth = template_auth.replace('{-repository-}', options.repo)
        witheverything_auth = withrepo_auth.replace('{-adminuser-}', options.adminuser )
        
except IOError :
    cli_parser.error( "Repository auth template do not exist (RTFM)")
else :
    try:
        config_file_auth = open(options.authdir + options.repo + '-svnauthz' ,'w')
        config_file_auth.write(witheverything_auth)
        config_file_auth.close()
        lchown(options.authdir + options.repo + '-svnauthz',0,apachegid)
        chmod(options.authdir + options.repo + '-svnauthz',0640)
        
    except IOError :
        cli_parser.error( "Can't write svnauthz files")

print "Please enter the desired password for: " + options.adminuser  
admin_user = call(['/usr/sbin/htpasswd2','-c',options.authdir + options.repo + '-passwdfile' ,options.adminuser])

# value > 0 when errors found..
if  not admin_user > 0:
	lchown(options.authdir + options.repo + '-passwdfile',0,apachegid)
	chmod(options.authdir + options.repo + '-passwdfile',0640)
	
try:
		# how to select the filesystem type ? ( a case of WITFM)
		#core.apr_initialize()
		#pool = core.svn_pool_create(None)
		#repos.svn_repos_create(options.location + options.repo, '', '', None, { fs.SVN_FS_CONFIG_FS_TYPE: .options.filesystem }, pool)
		#core.svn_pool_destroy(pool)
		#core.apr_terminate()
		
		# lets try the dirty way..
		create = call(["svnadmin", "create", "--fs-type", options.filesystem, options.location + options.repo])
except OSError:
	print "Failed to create the repository"
else:
	for dire in ['dav','db','locks']:
		lchown(options.location + options.repo + sep + dire,apacheuid,apachegid)
		for root, dirs, files in walk(options.location + options.repo + sep + dire , topdown=False):
			for name in files :
				lchown(join(root, name),apacheuid,apachegid)
			for name in dirs:
				lchown(join(root, name),apacheuid,apachegid)
				
	print "Reloading apache.."   
	restart_apache= call(["/etc/init.d/apache2", "reload"])
	print "Basic repository setup complete ..Have a lot of Fun.. ;-)"
