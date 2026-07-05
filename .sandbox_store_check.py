import sys
from pathlib import Path
sys.path.insert(0, str(Path('/mnt/c/Temp/kitian')))

from kitian.store import kitian_store
initial = kitian_store.get()
print('initial_core', initial['core'])
kitian_store.merge({'core': {'status': 'active'}})
print('after_merge', kitian_store.get()['core'])
kitian_store.reset()
print('after_reset', kitian_store.get()['core'])
kitian_store.merge({'directorMode': 2, 'director': {'mode': 2, 'label': 'Autónomo'}})
print('director_merge', kitian_store.get()['director'])
print('status_ok')
