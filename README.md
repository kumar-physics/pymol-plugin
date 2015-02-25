# pymol-plugin
PyMOL plugin to load EPPIC protein-protein interfaces
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
