# Part of the Cellular potts model package written by Bhaskar Kumawat (@aVeryStrangeLoop)
# Filename : config.py
# Contains : configuration for running the solver
# Dependencies : numpy
import copy
import numpy as np
import random
import math
import sys

class cConfig:
    ### Configuration class contains all user-define parameters required during runtime  
    ### Change the following parameters as per liking
     
    TYPES = np.array([0,1,2]) # Possible states of the system, given as a numpy array, each state type has an idx 
    ### Light = 0 , Dark = 1, Medium = 2
    # Number of cells of each type    
    TOTAL_SPINS = 201 # Number of cells/spins
    SPINS = np.array(range(TOTAL_SPINS))# Each grid-cell has a spin from this set 
    
    # MAKE SURE YOU HAVE ENOUGH CELLS TO ACCOMODATE THE MAX TARGET AREA * TOTAL_SPINS limit
    WORLD_X = 50 # Cells in X direction
    WORLD_Y = 50 # Cells in y direction

    SAMPLING_TYPE = 0 #Mutation sampling
    ### 0 = neighbor sampling
    ### 1 = global sampling, flip mutant to any spins in the world
    
    DEBUG_MODE = False # Set to True to get a verbose output

    BOUNDARY_MODE = 0 # How are boundary conditions handled
    ### 0 = periodic
    ### 1 = skip boundary neighbors in hamiltonian calculations
    ### 2 = Give special energy value to boundary cells

    BOUNDARY_ENERGIES = np.array([100.,100.,0.]) # Applicable if BOUNDARY_MODE = 2, interaction energy of boundary and type
    # Here a small energy cost present for non medium cells to be near the boundary


    MODE = 0 # Monte-carlo mode (0 = Constant temperature, 1 = cooling)

    steps = 2500000 # Total number of steps for monte_carlo(mode=0)/simulated annealing(mode=1)

    save_every = 1000 # Save system state every <save_every> steps

    ## Monte-Carlo temperature (if mode==0)
    temp_constant = 0.1
    
    ## Cooling properties (if mode ==1)
    temp_init = 1000.0 # Initial temperature (Only applicable if mode==1)
    temp_final = 0.1 # Final temperature (Only applicable if mode==1)

    def H(self,state):
        # Hamiltonian calculation for a given grid state
        spins = state[0]
        spin_types = state[1]
        # Write your own code here to output the hamiltonian given a system configuration
        if self.DEBUG_MODE:
            print("Calculating hamiltonian")
        
        # Parameters for glazier model
        def J(s1,s2):
            J00 = 14. # Surface energy between 0-0 (light-light)
            J11 = 2. # Surface energy between 1-1 (dark-dark)
            J22 = 0. # Surface energy between 2-2 (med-med)


            J01 = 11. # Surface energy between 0-1 (light-dark)
        
            J12 = 16. # Surface energy between 1-2 (dark-medium)
            J02 = 16. # Surface energy between 0-2 (light-medium)
            
            if (s1==0 and s2==0):
                return J00
            elif (s1==1 and s2==1):
                return J11
            elif (s1==2 and s2==2):
                return J22
            elif (s1==0 and s2==1) or (s1==1 and s2==0):
                return J01
            elif (s1==1 and s2==2) or (s1==2 and s2==1):
                return J12
            elif (s1==0 and s2==2) or (s1==2 and s2==0):
                return J02

        lambda_area = 10. # Strength of area constraint

        target_areas = [10.,10.,-1] # Target area for the three cell types (light,dark,med)

        def theta(target_area):
            if target_area > 0:
                return 1.
            elif target_area < 0 :
                return 0.
        
        def delta(t1,t2): # Delta function
            if t1==t2:
                return 1.
            else:
                return 0.

        h = 0.0

        X = spins.shape[0]
        Y = spins.shape[1]
        spin_areas = np.zeros(self.TOTAL_SPINS) # Areas of all cells
        
        # Add interaction energies (and count area of each state)
        for i in range(X):
            for j in range(Y):
                self_spin = spins[i,j]
                self_type = spin_types[self_spin]
                spin_areas[self_spin]+=1 # add to total area of this spin
                neighbor_spins = []
                #left neighbor
                if self.BOUNDARY_MODE == 0: # Periodic boundaries
                    neighbor_spins.append(spins[i-1,j] if i-1>=0 else spins[X-1,j])
                    neighbor_spins.append(spins[i+1,j] if i+1<=X-1 else spins[0,j])
                    neighbor_spins.append(spins[i,j-1] if j-1>=0 else spins[i,Y-1])
                    neighbor_spins.append(spins[i,j+1] if j+1<=Y-1 else spins[i,0])
                elif self.BOUNDARY_MODE == 1: # Blocked boundaries
                    if i-1>=0:
                        neighbor_spins.append(spins[i-1,j])
                    if i+1<=X-1:
                        neighbor_spins.append(spins[i+1,j])
                    if j-1>=0:
                        neighbor_spins.append(spins[i,j-1])
                    if j+1<=Y-1:
                        neighbor_spins.append(spins[i,j+1])
                elif self.BOUNDARY_MODE == 2: # Boundary interaction energies
                    neighbor_spins.append(spins[i-1,j] if i-1>=0 else -1)
                    neighbor_spins.append(spins[i+1,j] if i+1<=X-1 else -1)
                    neighbor_spins.append(spins[i,j-1] if j-1>=0 else -1)
                    neighbor_spins.append(spins[i,j+1] if j+1<=Y-1 else -1)

                for idx in range(len(neighbor_spins)): 
                    neighbor_spin = neighbor_spins[idx]
                    if neighbor_spin != -1:
                        h += J(spin_types[self_spin],spin_types[neighbor_spin])*(1.-delta(self_spin,neighbor_spin))
                    elif neighbor_spin == -1:
                        h += 2. * self.BOUNDARY_ENERGIES[spin_types[self_spin]]  # Add boundary energy value based on spin type
                        # NOTE: Doubled here because hamiltonian is halved later on
        
        h = h/2. # compensate for double counting of neighbor pairs
        
        # Add area constraint energies
        for idx in range(self.TOTAL_SPINS): # For each spin 
            a = spin_areas[idx]
            A = target_areas[spin_types[idx]] # Target area for the type for this spin
            h = h + lambda_area * theta(A) * math.pow((a-A),2)

        return h
     

    def Mutator(self,state):
        ## If conserved status is false, mutate only one cell
        spins = state[0]
        spin_types = state[1]
        
        if self.SAMPLING_TYPE == 0:
            if np.max(spins)==np.min(spins):
                print("All spins same in world, Neighbor sampling not possible!")
                exit(0)

            i1 = -1
            i2 = -1
            j1 = -1
            j2 = -1

            spin1 = -1
            spin2 = -1
            while spin1==spin2:
                # Choose a random cell and change its spin to spin of one of its neighbors given these two spins are not the same
                i1 = random.randrange(0,spins.shape[0])
                j1 = random.randrange(0,spins.shape[1])
                spin1 = spins[i1,j1]
                #neighbor_chosen = False
            
                #while not neighbor_chosen:           
                randir = random.choice([[0,1],[1,0],[0,-1],[-1,0]])
            
                i2 = i1 + randir[0]
                j2 = j1 + randir[1]

                    #if not (i2>=spins.shape[0] or i2<0 or j2>=spins.shape[1] or j2<0): 
                     #   neighbor_chosen = True
                if i2>=spins.shape[0]:
                    i2 = 0
                elif i2<0:
                    i2 = spins.shape[0]-1
                if j2>=spins.shape[1]:
                    j2 = 0
                elif j2<0:
                    j2 = spins.shape[1]-1


                spin2 = spins[i2,j2]
                        
            mut = np.copy(spins)
            mut[i1,j1] = spin2
            if self.DEBUG_MODE:
                print("Flipping spin %d to %d at (%d,%d) and (%d,%d) resp." % (spin1,spin2,i1,j1,i2,j2))
            return [mut,spin_types]
        
        elif self.SAMPLING_TYPE==1:
            i1 = random.randrange(0,spins.shape[0])
            j1 = random.randrange(0,spins.shape[1])
            spin1 = spins[i1,j1]
            spin2 = spin1
            while spin1 == spin2:
                spin2 = random.choice(self.SPINS)
            
            mut = np.copy(spins)
            mut[i1,j1] = spin2
            if self.DEBUG_MODE:
                print("Flipping spin %d at (%d,%d) to %d" % (spin1,i1,j1,spin2))
            return [mut,spin_types]
            
            

    def InitSys(self):
        # Sets the initial configuration of the system
        # Randomly from given types and spins. State of the system is defined by the list [types,spins]
        init_spins = np.random.choice(self.SPINS,(self.WORLD_X,self.WORLD_Y))
        spin_types = np.append(np.random.choice(self.TYPES[:-1],(self.TOTAL_SPINS-1)),[2]) # This array contains the type associated with each spin
        # spin_types[i] = type associated with spin no. i
        if self.DEBUG_MODE:
            print("Initialised configuration,")
            print(init_spins)
            print(spin_types)
        return [init_spins,spin_types]
        

    def SpinsToTypes(self,state):
        spins = state[0]
        spin_types = state[1]
        types = np.zeros(spins.shape)
        for i in range(spins.shape[0]):
            for j in range(spins.shape[1]):
                types[i,j] = spin_types[spins[i,j]]
        return types


if __name__=="__main__":
    print("Running in hamiltonian check mode, to use for actual runs run main.py instead!")
    
    conf = cConfig()

    spinsfile = sys.argv[1]
    typesfile = sys.argv[2]
    
    spins = np.loadtxt(spinsfile)
    types = np.loadtxt(typesfile)
    spins = spins.astype('int')
    types = types.astype('int')

    print("Hamiltonian of given configuration: %f" % (conf.H([spins,types])))
