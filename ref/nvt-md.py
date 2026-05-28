#####################################################################################
# NVT-MD simulations of CD47-SIRPa binding                                          #
# Written by HU Lab, 2023-03-22                                                     #
# Initial configuration file in xml format and trajectory in dcd format             #
# NOTE: 1. DO NOT change N_TIMESTEPS & FREQ_TRAJ for restart simulations!!!         #
#       2. Last frame of a dcd file overlaps with first frame of consecutive dcd!!! #
#####################################################################################
#!/usr/bin/python
import os, re, random
from poetry import cu_gala as gala
from poetry import _options

## >> Parameters & Constants << ##
RESTART     = True                           # restart simulation
TEMP        = 1.1                            # temperature, in units of $\epsilon / k_B$
DELTA_T     = 0.01                           # time step
N_TIMESTEPS = 10000000                       # number of integration steps
FREQ_TRAJ   = 10000                          # frequency of saving trajectory, i.e., sampling frequency
FREQ_SORT   = 200                            # frequency of memory sorting
DUMP_FILE   = 'dump.tsv'                     # dump file incl. timestep, momentum, pressure tensor, temperature, totoal potential, pressure
TRAJ_NAME   = 'traj'                         # name of trajectory
XML_NAME    = 'cpt'                          # name of checkpoint xml file (naming style: cpt.00001000000.xml)
RAND_SEED   = random.randint(1000, 99999999) # seed of pseudo random number generator
TWO_SIXTH   = 2.0**(1.0/6.0)

## Initialize ##
### Fetch initial configuration xml file: cpt.xxxxxxxxxx.xml ###
xml_list = []
for file in os.listdir(os.getcwd()):
    if file.startswith(XML_NAME) and file.endswith('.xml'):
        xml_list.append(file)
xml_list.sort(key=lambda x:[int(c) if c.isdigit() else c for c in re.split(r'(\d+)', x)])
INIT_XML = str(xml_list[-1])
xml_list = []

### Reset time_step="0" in cpt.0000000000.xml ###
create_time = os.path.getctime(INIT_XML)
if INIT_XML == XML_NAME + '.0000000000.xml':
    with open(INIT_XML, 'r') as file:
        original_contents = file.read()
    new_contents = re.sub(r'time_step="[^\"]*"', 'time_step="0"', original_contents)
    with open(INIT_XML, 'w') as file:
        file.write(new_contents)
modification_time = os.path.getmtime(INIT_XML)
os.utime(INIT_XML, (modification_time, create_time))

### Read xml ###
build_method = gala.XMLReader(INIT_XML)
perform_config = gala.PerformConfig(_options.gpu)
all_info = gala.AllInfo(build_method, perform_config)
app = gala.Application(all_info, DELTA_T)

## >> Force field << ##

### Bonded forces: FENE + Harmonic. NOTE that WCA is excluded from FENE here! c.f. https://pygamd-v1.readthedocs.io/en/latest/cuda/cu-forcefield-bonded-bond.html#BondForceFENE ###
BF_Tabs = [ {'type':'H-T',  'FENE':{'K': 30.0, 'rm': 1.5}, 'HARM':{'K':   0.0, 'r0': .95}}, \
            {'type':'T-T1', 'FENE':{'K': 30.0, 'rm': 1.5}, 'HARM':{'K':   0.0, 'r0': .95}}, \
            {'type':'H-T1', 'FENE':{'K':  0.0, 'rm': 1.5}, 'HARM':{'K':  10.0, 'r0': 4.0}}, \
            {'type':'RH-RT','FENE':{'K':  0.0, 'rm': 1.5}, 'HARM':{'K': 100.0, 'r0': 1.0}}, \
            {'type':'RT-RT','FENE':{'K':  0.0, 'rm': 1.5}, 'HARM':{'K': 100.0, 'r0': 1.0}}, \
            {'type':'RH-RE','FENE':{'K':  0.0, 'rm': 1.5}, 'HARM':{'K': 100.0, 'r0': 1.0}}, \
            {'type':'RE-RE','FENE':{'K':  0.0, 'rm': 1.5}, 'HARM':{'K': 100.0, 'r0': 1.0}}, \
            {'type':'RE-RB','FENE':{'K':  0.0, 'rm': 1.5}, 'HARM':{'K': 100.0, 'r0': 1.0}}, \
            {'type':'LH-LT','FENE':{'K':  0.0, 'rm': 1.5}, 'HARM':{'K': 100.0, 'r0': 1.0}}, \
            {'type':'LT-LT','FENE':{'K':  0.0, 'rm': 1.5}, 'HARM':{'K': 100.0, 'r0': 1.0}}, \
            {'type':'LH-LE','FENE':{'K':  0.0, 'rm': 1.5}, 'HARM':{'K': 100.0, 'r0': 1.0}}, \
            {'type':'LE-LE','FENE':{'K':  0.0, 'rm': 1.5}, 'HARM':{'K': 100.0, 'r0': 1.0}}, \
            {'type':'LE-LB','FENE':{'K':  0.0, 'rm': 1.5}, 'HARM':{'K': 100.0, 'r0': 1.0}} ]

### Angle bending forces ###
AF_Tabs = [ {'type':'RH-RT-RT', 'COS':{'K':100.0, 'theta0':180.0}}, \
            {'type':'RT-RT-RT', 'COS':{'K':100.0, 'theta0':180.0}}, \
            {'type':'RT-RH-RE', 'COS':{'K':100.0, 'theta0':180.0}}, \
            {'type':'RH-RE-RE', 'COS':{'K':100.0, 'theta0':180.0}}, \
            {'type':'RE-RE-RE', 'COS':{'K':100.0, 'theta0':180.0}}, \
            {'type':'RE-RE-RB', 'COS':{'K':100.0, 'theta0':180.0}}, \
            {'type':'LH-LT-LT', 'COS':{'K':100.0, 'theta0':180.0}}, \
            {'type':'LT-LT-LT', 'COS':{'K':100.0, 'theta0':180.0}}, \
            {'type':'LT-LH-LE', 'COS':{'K':100.0, 'theta0':180.0}}, \
            {'type':'LH-LE-LE', 'COS':{'K': 10.0, 'theta0':180.0}}, \
            {'type':'LE-LE-LE', 'COS':{'K': 10.0, 'theta0':180.0}}, \
            {'type':'LE-LE-LB', 'COS':{'K': 10.0, 'theta0':180.0}} ]
            
### Nonbonded pair forces: LJ & VCOS ###
'''
  V_{\rm cos}(r) = -\epsilon + \alpha 4 \epsilon [(\sigma/r)^{12}-(\sigma/r)^6 + 1/4], \quad r < 2^{1/6}\sigma \\
                 = -\epsilon \cos^2[(r-2^{1/6}\sigma)/(2w_{\rm c})], \quad 2^{1/6}\sigma \le r \le 2^{1/6}\sigma + w_{\rm c} \\
                 = 0, \quad r > 2^{1/6}\sigma + w_{\rm c}
  c.f. http://dx.doi.org/10.1063/1.2135785, Eq. (4)
'''
PF_Tabs = [ # Lipid-Lipid WCA
            {'pair':{'atom1':'H', 'atom2':'H'},   'strength': 1.0,  'range': .95, 'alpha': 1.0, 'rcut': .95 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'H', 'atom2':'T'},   'strength': 1.0,  'range': .95, 'alpha': 1.0, 'rcut': .95 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'H', 'atom2':'T1'},  'strength': 1.0,  'range': .95, 'alpha': 1.0, 'rcut': .95 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            # Lipid-Protein WCA
            {'pair':{'atom1':'H', 'atom2':'RH'},  'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'H', 'atom2':'RT'},  'strength': 10.0, 'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'H', 'atom2':'RE'},  'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'H', 'atom2':'RB'},  'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'H', 'atom2':'LH'},  'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'H', 'atom2':'LT'},  'strength': 5.0, 'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'H', 'atom2':'LE'},  'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'H', 'atom2':'LB'},  'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'T', 'atom2':'RH'},  'strength': 10.0, 'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'T', 'atom2':'RE'},  'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'T', 'atom2':'RB'},  'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'T', 'atom2':'LH'},  'strength': 5.0, 'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'T', 'atom2':'LE'},  'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'T', 'atom2':'LB'},  'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'T1', 'atom2':'RH'}, 'strength': 5.0, 'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'T1', 'atom2':'RE'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'T1', 'atom2':'RB'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'T1', 'atom2':'LH'}, 'strength': 5.0, 'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'T1', 'atom2':'LE'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'T1', 'atom2':'LB'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            # Protein-Protein WCA
            {'pair':{'atom1':'RH', 'atom2':'RH'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RH', 'atom2':'RT'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RH', 'atom2':'RE'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RH', 'atom2':'RB'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RH', 'atom2':'LH'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RH', 'atom2':'LT'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RH', 'atom2':'LE'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RH', 'atom2':'LB'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RT', 'atom2':'RT'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RT', 'atom2':'RE'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RT', 'atom2':'RB'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RT', 'atom2':'LH'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RT', 'atom2':'LT'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RT', 'atom2':'LE'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RT', 'atom2':'LB'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RE', 'atom2':'RE'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RE', 'atom2':'RB'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RE', 'atom2':'LH'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RE', 'atom2':'LT'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RE', 'atom2':'LE'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RE', 'atom2':'LB'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RB', 'atom2':'RB'}, 'strength': 10.0, 'range': 1.5, 'alpha': 1.0, 'rcut': 3.5 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RB', 'atom2':'LH'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RB', 'atom2':'LT'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RB', 'atom2':'LE'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'RB', 'atom2':'LB'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'LH', 'atom2':'LH'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'LH', 'atom2':'LT'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'LH', 'atom2':'LE'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'LH', 'atom2':'LB'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'LT', 'atom2':'LT'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'LT', 'atom2':'LE'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'LT', 'atom2':'LB'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'LE', 'atom2':'LE'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'LE', 'atom2':'LB'}, 'strength': 1.0,  'range': 1.0, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            {'pair':{'atom1':'LB', 'atom2':'LB'}, 'strength': 10.0, 'range': 1.5, 'alpha': 1.0, 'rcut': 3.5 * TWO_SIXTH, 'func': gala.PairFunc.lj12_6}, \
            # Lipid/Protein Tail-Tail VCOS + WCA
            {'pair':{'atom1':'T', 'atom2':'T'},   'strength': 1.0, 'range': 1.6, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH + 1.6, 'func': gala.PairFunc.cos_wc}, \
            {'pair':{'atom1':'T', 'atom2':'T1'},  'strength': 1.0, 'range': 1.6, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH + 1.6, 'func': gala.PairFunc.cos_wc}, \
            {'pair':{'atom1':'T', 'atom2':'RT'},  'strength': 1.0, 'range': 1.6, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH + 1.6, 'func': gala.PairFunc.cos_wc}, \
            {'pair':{'atom1':'T', 'atom2':'LT'},  'strength': 1.0, 'range': 1.6, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH + 1.6, 'func': gala.PairFunc.cos_wc}, \
            {'pair':{'atom1':'T1', 'atom2':'T1'}, 'strength': 1.0, 'range': 1.6, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH + 1.6, 'func': gala.PairFunc.cos_wc}, \
            {'pair':{'atom1':'T1', 'atom2':'RT'}, 'strength': 1.0, 'range': 1.6, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH + 1.6, 'func': gala.PairFunc.cos_wc}, \
            {'pair':{'atom1':'T1', 'atom2':'LT'}, 'strength': 1.0, 'range': 1.6, 'alpha': 1.0, 'rcut': 1.0 * TWO_SIXTH + 1.6, 'func': gala.PairFunc.cos_wc} ]

### Receptor-ligand binding force, four-body ###
'''
  U_{\rm bind} = U(r) * f_1(\theta_1) * f_2(\theta_2)
    U(r) = -\epsilon - U_{\rm c}, r <= 2^{1/6} \sigma + w_{\rm f}
         = 4 \epsilon {[\sigma/(r-w_{\rm f})]^{12} - [\sigma/(r-w_{\rm f})]^6} - U_{\rm c}, 2^{1/6} \sigma + w_{\rm f} < r < r_{\rm c} = w_{\rm f} + 2.5 \sigma
         = 0, r >= r_{\rm c}
    with U_{\rm c} = 4 \epsilon [(1/2.5)^{12} - (1/2.5)^6] = -0.01631689114 \epsilon
    f_1(\theta_1) = 1.0, \theta_1 <= \theta_{1,0}
                  = \exp {-K_1 (\theta_1 - \theta_{1,0})^2}, \theta_1 > \theta_{1,0}
    f_2(\theta_2) = 1.0, \theta_2 <= \theta_{2,0}
                  = \exp {-K_2 (\theta_2 - \theta_{2,0})^2}, \theta_2 > \theta_{2,0}
  * particle indices: 2--1 ... 3--4
'''
RLF_Tabs = [ {'pair':{'atom1':'RB', 'atom2':'LB'}, 'epsilon': 15.0, 'sigma': 0.95, 'wf': 0.4, 'rcut': 2.9, 'K1': 15.0, 'K2': 15.0, 'theta10': 10.0, 'theta20': 10.0} ]

## Create force related objects ##

### Bonded force: FENE ###
BFF = gala.BondForceFENE(all_info)
for n in range(0, len(BF_Tabs)):
  table = BF_Tabs[n]
  BFF.setParams(table['type'], table['FENE']['K'], table['FENE']['rm'])
app.add(BFF)

### Bonded force: Harmonic ###
BFH = gala.BondForceHarmonic(all_info)
for n in range(0, len(BF_Tabs)):
  table = BF_Tabs[n]
  BFH.setParams(table['type'], table['HARM']['K'], table['HARM']['r0'])
app.add(BFH)

### Bonded force: Angle bending ###
AF = gala.AngleForceCos(all_info)
for n in range(0, len(AF_Tabs)):
  table = AF_Tabs[n]
  AF.setParams(table['type'], table['COS']['K'], table['COS']['theta0'])
app.add(AF)

### Build neighbor list ###
NL_RCUT = max([PF_Tabs[i]['rcut'] for i in range(0, len(PF_Tabs))]) # NOTE: Maximum cutoff of pair forces used for building neighbor list!
NL_RBUF = 0.5                                                       # NOTE: Choose the optimal value for best performance!

NL = gala.NeighborList(all_info, NL_RCUT, NL_RBUF) # (,rcut,rbuffer)
for n in range(0, len(PF_Tabs)):
  table = PF_Tabs[n]
  NL.setRCutPair(table['pair']['atom1'], table['pair']['atom2'], table['rcut'])

for n in range(0, len(RLF_Tabs)):
  table = RLF_Tabs[n]
  NL.setRCutPair(table['pair']['atom1'], table['pair']['atom2'], table['rcut'])

### Nonbonded pair forces: LJ + VCOS ###
PF = gala.PairForce(all_info, NL)
for n in range(0, len(PF_Tabs)):
  table = PF_Tabs[n]
  PF.setParams(table['pair']['atom1'], table['pair']['atom2'], table['strength'], table['range'], table['alpha'], table['rcut'], table['func'])
app.add(PF)

### Nonbonded forces: Receptor-ligand binding force, four-body RE--RB ... LB--LE ###
group_RL = gala.ParticleSet(all_info, ['RB', 'LB'])
RLF = gala.RLBindingForce(all_info, NL, group_RL)
RLF.setShiftID(-1)
RLF.setGaussianMode(False)
for n in range(0, len(RLF_Tabs)):
  table = RLF_Tabs[n]
  RLF.setParams(table['pair']['atom1'], table['pair']['atom2'], table['epsilon'], table['sigma'], table['wf'], table['rcut'], table['K1'], table['K2'], table['theta10'], table['theta20'])
app.add(RLF)

## Integrate Newton's equation of motion ##
group_all = gala.ParticleSet(all_info, 'all')
comp_info = gala.ComputeInfo(all_info, group_all)
NVT = gala.LangevinNVT(all_info, group_all, TEMP, RAND_SEED) # Langevin thermostat with T = TEMP and \gamma = 1.0
NVT.setBussiParrinello(True)
app.add(NVT)

## Memory sorting ##
sort_method = gala.Sort(all_info)
sort_method.setPeriod(FREQ_SORT)
app.add(sort_method)

## Zero center-of-mass linear momentum during relaxation run, but not during production run ##
if RESTART != True:
  ZM = gala.ZeroMomentum(all_info)
  ZM.setPeriod(N_TIMESTEPS // 100)
  app.add(ZM)

## Dump momentum, pressure tensor, temperature, energy, etc. ##
DInfo = gala.DumpInfo(all_info, comp_info, DUMP_FILE)
DInfo.setPrecision(10)
DInfo.setPeriod(FREQ_TRAJ)
DInfo.dumpPressTensor()
DInfo.dumpPotential(RLF)
app.add(DInfo)

## Write trajectory ##
dcd_dump = gala.DCDDump(all_info, TRAJ_NAME, True)
dcd_dump.setPeriod(FREQ_TRAJ)
dcd_dump.unpbc(True) # output continous coordinates without applying periodic boundary condition
app.add(dcd_dump)

## Write protein coordinates: DCD + XML for conversion to XYZ ##
g_RL = gala.ParticleSet(all_info, ['RH', 'RT', 'RE', 'RB', 'LH', 'LT', 'LE', 'LB'])
dcd_RL = gala.DCDDump(all_info, g_RL, 'RL', True)
dcd_RL.setPeriod(10)
dcd_RL.unpbc(True)
app.add(dcd_RL)

xml_RL = gala.XMLDump(all_info, g_RL, 'RL')
xml_RL.setPrecision(12)
xml_RL.setPeriod(N_TIMESTEPS)
app.add(xml_RL)

## Save checkpoint for restart ##
xml_dump = gala.XMLDump(all_info, XML_NAME)
xml_dump.setPrecision(12)
xml_dump.setPeriod(N_TIMESTEPS)
xml_dump.setOutput(['position', 'image', 'velocity', 'force', 'mass', 'bond', 'angle'])
app.add(xml_dump)

## Run ##
app.run(N_TIMESTEPS)

## Write other info. ##
NL.printStats() # output neighbor list info.
print('INFO : --- Other parameters:')
print('INFO : Restart from previous simulation:', RESTART)
print('INFO : Temperature:', TEMP)
print('INFO : Integration stepsize:', DELTA_T)
print('INFO : Time steps:', N_TIMESTEPS)
print('INFO : Random seed:', RAND_SEED)