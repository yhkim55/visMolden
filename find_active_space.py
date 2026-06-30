import sys

def get_occup(molden_fn):
    '''
    Takes a molden file and returns list of orbital occupancies
    '''
    with open(molden_fn, 'r') as f:
        lines = f.readlines()
        lines = [line.strip() for line in lines]
    occup = [float(line.split()[1]) for line in lines if line.startswith('Occup')]
    return occup

def find_active_space(molden_fn):
    occup = get_occup(molden_fn)
    occup_as = []
    as_idx = []
    for i, occ in enumerate(occup):
        if occ > 0 and occ < 2:
            occup_as.append(occ)
            as_idx.append(i)
    return as_idx, occup_as

if __name__ == '__main__':
    molden_fn = sys.argv[1]
    active_space, occup = find_active_space(molden_fn)
    for n in active_space:
        print(n+1)
    print('----')
    for n in active_space:
        print(occup[n])
