from ViewerFramework.VFCommand import Command
from ViewerFramework.VF import LogEvent
import traceback,sys

class HostApp:
	"""
	support a host application in which ViewerFramework is embedded
	handle log event and execute interpreted command in the host app
	"""

	def __init__(self, vf, hostApp, debug=0):
        		
		self.vf = vf # ViewerFramework which is embedded
		self.driver = None # is set by self._setDriver 
		self.debug=debug
		# redirect stderr to file 
		# open file for logging commands executed by self.vf
		if self.debug == 1 :
			self.vf.pmvstderr=open('/tmp/pmvstderr','w')
			sys.stderr=self.vf.pmvstderr
			self.vf.abclogfiles=open('/tmp/logEvent','w')
			print 'logEvent',self.vf.abclogfiles			
		else:
			self.vf.pmvstderr=None
			self.vf.abclogfiles = None
		# create host application driver
		# this driver creates the connection between VF and the host application
		self.hostname = hostApp
		self._setDriver(hostApp)
		
		# register the function to be called when a log string is generated by VF
		# this function will create an equivalent cmd for the hot application
		# and have the host app run this command
		self.vf.registerListener(LogEvent, self.handleLogEvent)

		#Variable for the server-client mode
		self.servers = [] # list of (host, portNum) used to connect PMV server applications
		self._stop = False # set to True to stop executing commands sent by servers
		self.thread=None  # the thread used to apply the command from the server

	def _setDriver(self,hostApp):
		"""
		Define the host application and call the approriate command interpreter
		setDriver(hostApp)
		hostApp is  case in-sensitive string which can be 'Blender' or 'c4d'
		raises ValueError if the hostApp is invalid
		"""
		#from mglutil.hostappInterface import appliDriver
                from Pmv.hostappInterface import appliDriver
		#currently hostApp have to be c4d,blender or maya		
		self.driver=appliDriver.HostPmvCommand(soft=hostApp.lower())				
			
	def handleLogEvent(self, event):
		"""
		Function call everytime the embeded pmv create a log event, cf a command is execute with the keyword log=1
		"""
		import sys

		mesgcmd=''						#the message command string
		lines=event.logstr.split('\n')	#the last log event ie the last command string
		for line in lines :
			#parse and interprete the pmv command to generate the appropriate host appli command
			func,arg=self.driver.parseMessageToFunc(line)
			temp=self.driver.createMessageCommand(func,arg,line)
			mesgcmd+=temp
		if self.debug ==1 :
			self.vf.abclogfiles.write("################\n"+self.hostname+"_CMD\n"+mesgcmd+'\n')
			self.vf.abclogfiles.flush()
			self.vf.pmvstderr.flush()
		#try to exec the command generated, using keywords dictionary
		try:
			exec(mesgcmd, {'self':self.vf,'mv':self.vf,'pmv':self.vf})
		except :			
			import sys,traceback
			tb=traceback.format_exc()
			raise ValueError(tb)
			if self.debug ==1:
				#	tb = traceback.extract_tb(sys.exc_traceback)
				self.vf.abclogfiles.write("exeption\n"+str(tb)+"\n")
				self.vf.abclogfiles.flush()

	######Dedicated function for the client-server mode#################
	def runServerCommandLoop(self):
		"""
		Infinite loop which call the viewerframework runservercommand
		"""
		while not self._stop:		
			self.vf.runServerCommands()

	def setServer(self,address,port):
		"""
		Define the server,portnumeber of the server
		"""
		self.servers=[address,port]

	def start(self):
		"""
		Connect to the server and start the thread which permit the execution of the server command
		"""
		self.vf.socketComm.connectToServer(self.servers[0],self.servers[1],self.vf.server_cb)
		from Queue import Queue
		self.vf.cmdQueue = Queue(-1)
		import thread
		self._stop=False
		if self.thread==None : 
				self.thread=thread.start_new(self.runServerCommandLoop, ())
		if self.debug ==1:
				sys.stderr.write('ok thread\n')
				self.vf.pmvstderr.flush()

	def stop(self):
		#stop the infinite loop and diconect from the server
		self._stop=True
		self.vf.socketComm.disconnectFromServer(self.servers[0],self.servers[1])