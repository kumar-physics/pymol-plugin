# -*- coding: utf-8 -*-
# vim:noet ts=4 sw=4 ff=unix fenc=utf-8
'''
PyMOL plugin to load EPPIC interface files

DESCRIPTION

	EPPIC (www.eppic-web.org) stands for Evolutionary Protein-Protein Interface
	Classifier (Duarte et al, BMC Bionformatics, 2012).

	EPPIC mainly aims at classifying the interfaces present in protein crystal
	lattices in order to determine whether they are biologically relevant or
	not.

	For more information or queries please contact us at eppic@systemsx.ch. Our
	team web page is: http://www.psi.ch/lbr/capitani_-guido

INSTALLATION

	To install from within pymol, from the Plugins menu, choose 'Manage
	Plugins>Install...' and select fetch_eppic.py from your hard drive.

	To install manually, copy fetch_eppic.py to
	'PYMOLPATH/modules/pmg_tk/startup/' and restart pymol.

	After installation you will have an additional entry called "Eppic
	Interface Loader" in Plugin menu.

	Note: Users of MacPyMol.app do not have a plugins menu, and should use the
	fetch_eppic command.

USAGE--PLUGIN MENU

	Entering a PDB code will load all interfaces for a given pdbid.
	Example: 2gs2

	Single interfaces can also be selected. Interfaces are numbered according to the
	EPPIC website.

	By default, each interface is loaded as its own object. They can also be
	loaded as multiple states in a single object, which can then be navigated
	using the state navigation at the bottom right.

USAGE--COMMAND LINE
	fetch_eppic pdbCode [iface, [name, [state, [async, [entropies]]]]]

ARGUMENTS
	Arguments mirror arguments to fetch

	pdbid = string: PDB ID {required}

	iface = integer: EPPIC interface number, as listed on the EPPIC server
	(eppic-web.org). Use 0 to load all interfaces.

	name = string: name of the pymol object to save to. For multiple
	interfaces include the string '{}', which will be replaced with the
	interface number {default: <pdbid>-<iface>}

	state = integer: number of the state into which the content should be
	loaded, or 0 for append {default: 0}

	async = integer: 0 to force synchronous execution {default:1}

	entropies = mixed: specifies which chains to display "molecular potato"
	style sequence entropy. 0 for both chains, 1 for the first chain, or 2 for
	the second. Also accepts chains by letter. Other values will disable
	surface display. {default disabled}

	Other arguments will be passed directly to load.

EXAMPLES

	#Load all the interface files for 2gs2
	fetch_eppic 2gs2

	#Load only the second interface
	fetch_eppic 2gs2, 2

	#Load all interfaces as states of a single object
	fetch_eppic 2gs2, name=2gs2_eppic

	#Load synchronously for chaining commands
	fetch_eppic 2gs2, 1, name=interface, async=0; show cartoon, interface

	Interface ids are those listed in the EPPIC server output


Author   : Kumaran Baskaran & Spencer Bliven
Date     : 10.04.2014
Modified : 21.08.2014
Version  : 1.0-RC
'''
import sys, os, thread
import urllib2,StringIO,gzip
import pymol
from pymol import cmd, plugins, stored
from string import atoi

_version = "1.0-RC"


def hasTk():
	""" Make an educated guess as to whether Tk is installed,
	hopefully without triggering any installation on Macs
	"""
	#use of internal variable endorsed by Thomas Holder
	return pymol._ext_gui



# If we're in a Tkinter environment, register with the plugins menu
# Otherwise, only use command line version
if hasTk():

	try:
		from Tkinter import *
		import tkSimpleDialog
		import tkMessageBox


		def __init_plugin__(self=None):
			#print self.root.wm_title()
			print "Loaded fetch_eppic plugin version %s"%_version

			# Simply add the menu entry and callback
			plugins.addmenuitem('EPPIC Interface Loader Service', fetch_eppic_plugin)

		# Tk plugin version.
		def fetch_eppic_plugin():
			print "Getting PMGApp"
			app = plugins.get_pmgapp()
			print "Getting TK"
			root = plugins.get_tk_root()

			print "Getting panel"
			panel = EppicPanel(root)




		class EppicPanel:
			"Tk panel for eppic input"

			# Labels for mode options
			_MODE_ALL_SPLIT = u"All Interfaces–Several Objects"
			_MODE_ALL_JOINED = u"All Interfaces–Single Object"
			_MODE_SINGLE = u"Single Interface"

			_ENTROPY_NONE = u"Don't Display"
			_ENTROPY_BOTH = u"Both chains"
			_ENTROPY_LEFT = u"First chain"
			_ENTROPY_RIGHT = u"Second chain"

			def errorfn(self,msg,parent=None):
				tkMessageBox.showinfo('EPPIC Interface Loader Service', msg,
						parent=(parent or plugins.get_tk_root()) )

			def __init__(self, master):
				"""Initialize the GUI"""
				frame = Toplevel(master)
				frame.title("EPPIC Interface Loader Service")
				frame.minsize(300,0)
				#frame.resizable(0,0)

				self.frame = frame

				pad = 4
				padkw = {'padx': pad, 'pady': (pad, 0)}

				# All options. Note that changeMode is sensitive to changes in order here
				self.selectedMode = StringVar(frame)
				self.selectedMode.set(self._MODE_ALL_SPLIT)

				# Create OptionMenu with all options
				row = self._makerow("Type:",**padkw)
				mode = OptionMenu(row,self.selectedMode,
						self._MODE_ALL_SPLIT, self._MODE_ALL_JOINED, self._MODE_SINGLE,
						command=self.changeMode)
				mode.pack(side=LEFT)

				row = self._makerow("PDB ID",**padkw)
				self.pdbid = Entry(row,width=4)
				self.pdbid.bind("<Return>", self.submit)
				self.pdbid.pack(side=LEFT)

				self.ifacelabel = Label(row, text="Interface No.")
				self.ifacelabel.pack(side=LEFT)
				self.ifaceno = Entry(row,width=4)
				self.ifaceno.bind("<Return>", self.submit)
				self.ifaceno.pack(side=LEFT)

				# Create entropy options
				row = self._makerow("Show entropies:", **padkw)
				self.entropyAction = StringVar(frame)
				self.entropyAction.set(self._ENTROPY_NONE)

				entropy = OptionMenu(row, self.entropyAction,
						self._ENTROPY_NONE, self._ENTROPY_BOTH,self._ENTROPY_LEFT, self._ENTROPY_RIGHT )
				entropy.pack(side=LEFT)


				row = self._makerow(**padkw)
				cancel = Button(row, text="Cancel", command=self.cancel)

				ok = Button(row, text="OK", command=self.submit)
				ok.pack(side=RIGHT,fill=X)
				cancel.pack(side=RIGHT,fill=X)

				row = self._makerow(padx=pad, pady=(2,pad))
				self.keep = IntVar(frame)
				keep = Checkbutton(row, text="Keep dialog open",variable=self.keep)
				keep.pack(side=RIGHT)

				# Disable iface input
				self.changeMode()

				ok.focus_set()

			def _makerow(self,label=None,parent=None, **kwargs):
				"helper method for wrapping up rows in a frame"
				row = Frame(parent or self.frame)
				row.pack(fill=X,**kwargs)
				if label:
					Label(row, text=label).pack(side=LEFT)
				return row

			def changeMode(self,mode=None):
				"Disables/enables the interface input box depending on the mode dropdown"
				#print("Selected Mode is %s"%self.selectedMode.get())
				#print("Mode param is %s"%mode)
				if mode is None:
					mode = self.selectedMode.get()
				if mode == self._MODE_SINGLE: # Single interface
					self.ifacelabel.config(state=NORMAL)
					self.ifaceno.config(state=NORMAL)
				else: # all interfaces
					self.ifacelabel.config(state=DISABLED)
					self.ifaceno.config(state=DISABLED)

			def cancel(self):
				#self.errorfn("Cancel")
				self.frame.destroy()

			def submit(self,src=None):
				"Handles the OK button"

				pdbCode = self.pdbid.get().strip()
				iface = self.ifaceno.get().strip() #iface number as string
				mode = self.selectedMode.get()

				#Validate
				if len(pdbCode) != 4:
					self.errorfn("Invalid PDB Code",self.frame)
					return

				if mode == self._MODE_SINGLE: # Single interface
					if len(iface)<1:
						self.errorfn("No interface specified",self.frame)
						return
				else:
					iface = 0

				if mode == self._MODE_ALL_JOINED: # Single object
					name = "%s_eppic" % (pdbCode)
				else:
					name=None

				print("Fetching {}{}".format(pdbCode,"-"+iface if iface else ""))

				if self.entropyAction.get() == self._ENTROPY_BOTH:
					entropies = 0
				elif self.entropyAction.get() == self._ENTROPY_LEFT:
					entropies = 1
				elif self.entropyAction.get() == self._ENTROPY_RIGHT:
					entropies = 2
				else:
					entropies = None

				# Tk isn't thread safe, so we run synchronously.
				# We could also use events to communicate errors to the mainloop,
				# but this seems like too much work for a minor feature
				#thread.start_new_thread(fetch_eppic_sync, (pdbCode,None,0,self.errorfn))
				names = fetch_eppic_sync(pdbCode,iface,name,entropies=entropies,logfn=self.errorfn)

					

				if not self.keep.get():
					self.frame.destroy()

	except ImportError:
		pass #no Tk




from pymol import cmd
from string import atoi
import urllib2,StringIO,gzip
import gzip
import os

# Main command line version
def fetch_eppic(pdbCode,iface=0,name=None,state=0,async=1, entropies=None, **kwargs):
	'''
	===========================================================================
	DESCRIPTION

		EPPIC (www.eppic-web.org) stands for Evolutionary Protein-Protein Interface
		Classifier (Duarte et al, BMC Bionformatics, 2012).

		EPPIC mainly aims at classifying the interfaces present in protein crystal
		lattices in order to determine whether they are biologically relevant or not.

		For more information or queries please contact us at eppic@systemsx.ch.
		Our team web page is: http://www.psi.ch/lbr/capitani_-guido

		fetch_eppic is a command line tool to download interface files from
		EPPIC server to open in pymol

	USAGE--COMMAND LINE
		fetch_eppic pdbCode [iface, [name, [state, [async, [entropies]]]]]

	ARGUMENTS
		Arguments mirror arguments to fetch

		pdbid = string: PDB ID {required}

		iface = integer: EPPIC interface number, as listed on the EPPIC server
		(eppic-web.org). Use 0 to load all interfaces.

		name = string: name of the pymol object to save to. For multiple
		interfaces include the string '{}', which will be replaced with the
		interface number {default: <pdbid>-<iface>}

		state = integer: number of the state into which the content should be
		loaded, or 0 for append {default: 0}

		async = integer: 0 to force synchronous execution {default:1}

		entropies = mixed: specifies which chains to display "molecular potato"
		style sequence entropy. 0 for both chains, 1 for the first chain, or 2 for
		the second. Also accepts chains by letter. Other values will disable
		surface display. {default disabled}

		Other arguments will be passed directly to load.

	EXAMPLES

		#Load all the interface files for 2gs2
		fetch_eppic 2gs2

		#Load only the second interface
		fetch_eppic 2gs2, 2

		#Load all interfaces as states of a single object
		fetch_eppic 2gs2, name=2gs2_eppic

		#Load synchronously for chaining commands
		fetch_eppic 2gs2, 1, name=interface, async=0; show cartoon, interface

	Author : Kumaran Baskaran
	Date   : 11.04.2014
	===========================================================================
	'''
	if int(async):
		thread.start_new_thread(fetch_eppic_sync, (pdbCode,iface,name,state,entropies),kwargs)
	else:
		fetch_eppic_sync(pdbCode,iface,name,state,entropies,**kwargs)

# Helper version, does all the work
def fetch_eppic_sync(pdbCode,iface=0,name=None,state=0,entropies=None,logfn=None,**kwargs):
	"Synchronously fetch eppic interface(s)"
	fetchpath=cmd.get('fetch_path')
	if logfn is None:
		def logfn(m):
			print(m)

	try:
		if entropies is not None:
			entropies = int(entropies)
	except ValueError:
		pass

	if not pdbCode:
		logfn( "No PDB given")
		return

	fetched = []

	if iface: #Single interface
		filename=os.path.join(fetchpath, "%s-%s.pdb"%(pdbCode,iface))
		if name is None:
			name = "{}-{}".format(pdbCode,iface)
		#Download interface
		check_fetch = load_eppic(pdbCode,iface,filename,logfn)
		if check_fetch:
			cmd.load(filename,name,state,format="pdb",**kwargs)
			fetched.append(name)

			if entropies is not None:
				show_entropies(name,entropies)
			cmd.util.color_chains(name)
		else:
			logfn("No PDB or Interface Found")
	else: # All interfaces
		if name is None:
			name = "{}-{{}}".format(pdbCode)
		iface=1
		check_fetch = True
		while check_fetch:
			filename=os.path.join(fetchpath, "%s-%d.pdb"%(pdbCode,iface))
			objname = name.format(iface)
			check_fetch = load_eppic(pdbCode,iface,filename,logfn)
			if check_fetch:
				cmd.load(filename,objname,state,format="pdb",**kwargs)
				fetched.append(objname)

				if entropies is not None:
					show_entropies(objname,entropies)
				cmd.util.color_chains(objname)
				iface+=1
			else:
				if iface==1:
					logfn( "No PBD or Interface Found")
					logfn("No PDB or Interface Found")
	
	return fetched

def load_eppic(pdbid,ifaceid,filename,logfn=None):
	"""Download the interface from eppic
	return whether the download was successfull
	"""
	fetchurl="http://eppic-web.org/ewui/ewui/fileDownload?type=interface&id=%s&interface=%s"%(pdbid.lower(),ifaceid)

	is_done=False

	if logfn is None:
		def logfn(m):
			print(m)

	request=urllib2.Request(fetchurl)
	request.add_header('Accept-encoding', 'gzip')
	opener=urllib2.build_opener()
	try:
		f=opener.open(request)
		compresseddata = f.read()
		if len(compresseddata)>0:
			compressedstream = StringIO.StringIO(compresseddata)
			gzipper = gzip.GzipFile(fileobj=compressedstream)
			data = gzipper.read()
			try:
				open(filename,'w').write(data)
				is_done=True
			except IOError:
				logfn( "Error writing to "+filename)
	except urllib2.HTTPError:
		pass
	except IOError:
		pass
	return is_done


def show_entropies(srcObj,chainNo,name=None):
	"""Extracts the specified chain from srcObj and displays b-factors on the
	surface.

	chainNo: Either a string giving the chain to extract, a positive integer
	giving the number of the chain to extract (starting at 1), or 0 to extract
	all chains.

	name: Name of object to store the entropies. {default <srcObj>-<chain>_entropy
	"""
	if name is None:
		name = "{}-{{}}_entropy".format(srcObj)

	def append_if_different(arr,c):
		if len(arr) == 0 or arr[-1] != c:
			arr.append(c)
	stored._fetch_eppic_append_if_different = append_if_different

	if type(chainNo) == int:

		# Create list of chains
		stored._fetch_eppic_chain_ids = []
		cmd.iterate(srcObj,"stored._fetch_eppic_append_if_different(stored._fetch_eppic_chain_ids,chain)")

		if chainNo == 0:
			chains = stored._fetch_eppic_chain_ids
		else:
			#TODO input validation
			chains = [stored._fetch_eppic_chain_ids[chainNo-1]]
	else:
		chains = [chainNo]

	for chain in chains:
		# Create new object
		objname = name.format(chain)
		cmd.create( objname , "({}) and chain {}".format(srcObj,chain) )
		
		# Show entropies (stored in b factors)
		cmd.show_as('surface',"%s"%(objname))
		cmd.spectrum(expression='b',palette='rainbow',selection='%s'%(objname),
				minimum=0.0,maximum=3.3219280948873626)

cmd.extend("fetch_eppic",fetch_eppic)
