# This file shows some example usage of Python functions to read an OCT file.
# To use exectute this test reader, scroll to the bottom and pass an OCT file to the function open_OCTFile.
#
# Additional modules to be installed should be 'xmltodict' and 'shutil'
#
# This file can be called like below assuming you have only Python 3 installed
# 'python open_OCTFile.py'
# Alternative you can call for specific versions 3 or 3.8
# 'python3 open_OCTFile.py'
# 'python3.8 open_OCTFile.py'
#

import numpy as np
import matplotlib.pyplot as pp
import xmltodict
import os
import tempfile
import zipfile
import shutil
import json
import warnings
from warnings import warn
formatwarning_orig = warnings.formatwarning
warnings.formatwarning = lambda message, category, filename, lineno, line=None: \
    formatwarning_orig(message, category, filename='', lineno='', line='')


def open_OCTFile(filename):
    """
    Unzip the OCT file into a temp folder.

    :param filename:
    :return:
    """
    tempdir = tempfile.gettempdir()
    handle = dict()
    handle['filename'] = filename
    handle['path'] = os.path.join(tempdir, 'OCTData')



    named_oct_data_folder = os.path.join(handle['path'],os.path.basename(filename).strip('.oct'))
    handle['named_oct_data_folder'] = named_oct_data_folder
    if os.path.exists(named_oct_data_folder):
        warn('Reuse data in {}\n'.format(named_oct_data_folder))
    else:
        print('\nTry to extract {} into {}. Please wait.\n'.format(filename,named_oct_data_folder))
        if not os.path.exists(handle['path']):
            os.mkdir(handle['path'])
        if not os.path.exists(named_oct_data_folder):
            os.mkdir(named_oct_data_folder)

        with zipfile.ZipFile(file=handle['filename']) as zf:
            zf.extractall(path=named_oct_data_folder)

        # Thorlabs stores incompatible folder names in zip.
        # Need to create data explicitly.
        # walk_object = os.walk(named_oct_data_folder)
        # for root, dirs, files in walk_object:
        #     if not os.path.exists(os.path.join(named_oct_data_folder, 'data')):
        #         os.mkdir(os.path.join(named_oct_data_folder, 'data'))
        #     for file in files:
        #         if not 'Header.xml' in file:
        #             src = os.path.join(root, file)
        #             dst = os.path.join(root,'data',file.lstrip('data\\\\'))
        #             shutil.move(src,dst)

    # make folder 's' to indicate it is in use (open)
    if not os.path.exists(os.path.join(named_oct_data_folder,'s')):
        os.mkdir(os.path.join(named_oct_data_folder,'s'))
    else:
        warn('Folder \'s\' exists.')

    with open(os.path.join(named_oct_data_folder, 'Header.xml'),'rb') as fid:
        up_to_EOF = -1
        xmldoc = fid.read(up_to_EOF)

    handle_xml = xmltodict.parse(xmldoc)
    handle.update(handle_xml)
    return handle

def get_OCTDataFileProps(handle, data_name=None, prop=None):
    """
    List some of the properties as in the Header.xml.
    :param handle:
    :param data_name:
    :param prop:
    :return:
    """
    metadatas = handle['Ocity']['DataFiles']['DataFile']
    metadata = metadatas[np.argwhere([data_name in h['#text'] for h in handle['Ocity']['DataFiles']['DataFile']]).squeeze()]
    prop = metadata[prop]
    return prop

def get_OCTDataFileData(handle, data_name=None):
    """
    Examples how to extract specific data and reconstruct them based on the meta data.
    :param handle:
    :param data_name:
    :return:
    """
    dtypes = {'4':np.int32, '2':np.int16}
    rtypes = {'4':np.float32}
    metadatas = handle['Ocity']['DataFiles']['DataFile']
    metadata = metadatas[np.argwhere([data_name in h['#text'] for h in handle['Ocity']['DataFiles']['DataFile']]).squeeze()]
    print(metadata)
    if data_name in 'VideoImage':
        data_filename = os.path.join(handle['named_oct_data_folder'], metadata['#text'])
        dtype = dtypes[metadata['@BytesPerPixel']] # This is not consistent! unsigned and signed not distinguished!
        sizeX = int(metadata['@SizeX'])
        sizeZ = int(metadata['@SizeZ'])
        data = np.fromfile(data_filename, dtype).reshape([sizeX,sizeZ])
        data = abs(data)/abs(data).max()
        print(data.shape)
        print(data.min(), data.max())
        return data

    elif data_name in 'Intensity':
        data_filename = os.path.join(handle['named_oct_data_folder'], metadata['#text'])
        data_type = metadata['@Type'] # this is @Real
        dtype = rtypes[metadata['@BytesPerPixel']] # This is not consistent! unsigned and signed not distinguished!
        sizeX = int(metadata['@SizeX'])
        sizeZ = int(metadata['@SizeZ'])
        data = (np.fromfile(data_filename, dtype=(np.float32, [sizeX,sizeZ])))[0].T # there are two images. Take the first [0].
        return data

    else:
        warn('data_name {} not in properties.'.format(data_name))



def close_OCTFile(handle):
    """
    remove 's' folder.
    :param handle:
    :return:
    """

    if os.path.exists(os.path.join(handle['named_oct_data_folder'],'s')):
      os.rmdir(os.path.join(handle['named_oct_data_folder'], 's'))
    else:
      warn('Subfolder \'s\' as label not existing.')



# Example usage
handle = open_OCTFile('/Users/kai/Documents/Acer_mirror/sdb5/Sergey Alexandrov/srSESF_OCT_data/data/AfterCXL2D(2).oct');

# example to list properties
print('properties:')
print(handle.keys()) #list all keys in handle
print(handle['Ocity'].keys()) #list all keys in Ocity. This is from Header.xml
print(handle['Ocity']['Acquisition'].keys()) #list all keys in Acquisition
print(handle['Ocity']['MetaInfo']['Comment']) #get comment value from MetaInfo

print(handle['Ocity']['Acquisition']['RefractiveIndex'])
print(handle['Ocity']['Acquisition']['SpeckleAveraging'].keys())
fastaxis = handle['Ocity']['Acquisition']['SpeckleAveraging']['FastAxis']
print('Speckle Averaging FastAxis: ',fastaxis)
print(handle['Ocity']['Image'].keys())

# example list all data files
print('\n\ndata file names:')
[print(h['#text']) for h in handle['Ocity']['DataFiles']['DataFile']]

print(get_OCTDataFileProps(handle, data_name = 'VideoImage', prop='@Type')) #print type of video image
print(get_OCTDataFileProps(handle, data_name = 'Intensity', prop='@Type'))

import matplotlib
matplotlib.use('Qt5Agg') # Better GUI
from matplotlib.pyplot import *

# get and plot VideoImage
data = get_OCTDataFileData(handle, data_name = 'VideoImage')
figure(num='VideoImage')
imshow(data,cmap='Greys',vmin=0.0,vmax=0.4)
colorbar()

# get and plot IntensityImage
data = get_OCTDataFileData(handle, data_name = 'Intensity')
figure(num='Intensity')
imshow((data))
imshow(data,cmap='Greys_r',vmin=30,vmax=50)
colorbar()
show()

close_OCTFile(handle)