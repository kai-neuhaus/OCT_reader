"""
Testing and usage:

run this function at the end of this file ...

mat_data = OCTtoMATraw('test.oct')

Calling this function here directly is for testing.
The last command can be removed and then this OCT_converter can be imported:

import OCT_converter

mat_data OCT_converter.OCTtoMATraw('test.oct')

"""
import numpy as np
from scipy.fftpack import fft,ifft
from scipy.interpolate import interp1d
import matplotlib; matplotlib.use('Qt5Agg')
import matplotlib.pyplot as pp
import xmltodict
import os
import re
import zipfile
import json
import warnings
from warnings import warn
formatwarning_orig = warnings.formatwarning
warnings.formatwarning = lambda message, category, filename, lineno, line=None: \
    formatwarning_orig(message, category, filename='', lineno='', line='')

def shorten_dict_keys( in_dict ):
    '''
    The MAT format does not allow key lengths larger 31 characters.
    Remove special characters '@' and '#' from key names.
    This function returns a new dict looping over all keys and tries to reduce the string length.
    '''
    out_dict = {}
    for k,v in in_dict.items():
        if v is None:
            # raise(ValueError('v:{} is None key:{}'.format(v,k)))
            v = 'None'
        if len(k)>30:
            while len(k) > 30:
                k = ''.join([w[:-1] for w in re.findall('[A-Z][^A-Z]*', k)])
        if '#' in k: k = k.split('#')[1]
        if '@' in k: k = k.split('@')[1]
        if isinstance(v,dict):
            out_dict[k] = shorten_dict_keys(v)
        else:
            out_dict[k] = v
    return out_dict

def OCTtoMATraw(oct_filename):
    """
    Convert OCT to MAT file format.
    Keep all data raw; do not process.
    See test_OCT_convert.m of how to use.
    """
    # Create a python_types dictionary for required data types
    # I.e. the Thorlabs concept can mean a "Raw - signed - 2 bytes" --> np.int16
    python_dtypes = {'Colored': {4: np.int32, 2: np.int16},
                     'Real': {4: np.float32},
                     'Raw': {'signed': {1: np.int8, 2: np.int16},
                             'unsigned': {1: np.uint8, 2: np.uint16}}}
    mat_data = {}
    mat_data['Spectral'] = []
    mat_data['Spectral_apo'] = []
    with zipfile.ZipFile(file=oct_filename) as zf:
        mat_data['Header'] = xmltodict.parse(zf.read('Header.xml'))
        is_signed = mat_data['Header']['Ocity']['Instrument']['RawDataIsSigned'].replace('True','signed').replace('False','unsigned')
        mat_data['Header'] = shorten_dict_keys(mat_data['Header'])
        # create a separate DataFileDict
        mat_data['Header']['DataFileDict'] = {}
        for file_object in (mat_data['Header']['Ocity']['DataFiles']['DataFile']):
            print(file_object)
            inoct_filename = file_object['#text'].split('data\\')[1].split('.data')[0] #remove the data\\ part and '.data'
            mat_data['Header']['DataFileDict'][inoct_filename] = dict(shorten_dict_keys(file_object))
        mat_data['py_Header'] = json.dumps(mat_data['Header']) # For Python we need to use json

        S0arr_type = (mat_data['Header']['DataFileDict']['Spectral0']['Type'])
        S0SizeZ = int(mat_data['Header']['DataFileDict']['Spectral0']['SizeZ'])
        S0SizeX = int(mat_data['Header']['DataFileDict']['Spectral0']['SizeX'])
        S0bpp = int(mat_data['Header']['DataFileDict']['Spectral0']['BytesPerPixel'])
        S0ar_start = int(mat_data['Header']['DataFileDict']['Spectral0']['ApoRegionStart0'])
        S0ar_end = int(mat_data['Header']['DataFileDict']['Spectral0']['ApoRegionEnd0'])
        S0dtype = python_dtypes[S0arr_type][is_signed][S0bpp]

        # Single B-scans may contain only Spectral0.data
        if mat_data['Header']['DataFileDict'].get('Spectral1'):
            S1arr_type  = mat_data['Header']['DataFileDict']['Spectral1']['Type']
            S1SizeZ     = int(mat_data['Header']['DataFileDict']['Spectral1']['SizeZ'])
            S1SizeX     = int(mat_data['Header']['DataFileDict']['Spectral1']['SizeX'])
            S1bpp       = int(mat_data['Header']['DataFileDict']['Spectral1']['BytesPerPixel'])
            S1sr_start  = int(mat_data['Header']['DataFileDict']['Spectral1']['ScanRegionStart0'])
            S1sr_end    = int(mat_data['Header']['DataFileDict']['Spectral1']['ScanRegionEnd0'])
            S1dtype     = python_dtypes[S1arr_type][is_signed][S1bpp]

        for item in zf.filelist:
            print(item.filename)

            if 'Spectral0' in item.filename and mat_data['Header']['DataFileDict']['Spectral0'].get('ScanRegionStart0'):
                S0sr_start = int(mat_data['Header']['DataFileDict']['Spectral0']['ScanRegionStart0'])
                S0sr_end = int(mat_data['Header']['DataFileDict']['Spectral0']['ScanRegionEnd0'])
                data = np.frombuffer(zf.read(item.filename), dtype=(S0dtype, [S0SizeX, S0SizeZ]))[0]
                mat_data['Spectral'].append(data[S0sr_start:S0sr_end, :])
                mat_data['Spectral_apo'].append(data[S0ar_start:S0ar_end, :])
            elif 'Spectral0' in item.filename:
                data = np.frombuffer(zf.read(item.filename), dtype=(S0dtype, [S0SizeX, S0SizeZ]))[0]
                mat_data['Spectral_apo'].append(data)

            elif 'Spectral1' in item.filename and mat_data['Header']['DataFileDict']['Spectral1'].get('ApoRegionStart0'):
                S1ar_start = int(mat_data['Header']['DataFileDict']['Spectral1']['ApoRegionStart0'])
                S1ar_end = int(mat_data['Header']['DataFileDict']['Spectral1']['ApoRegionEnd0'])
                data = np.frombuffer(zf.read(item.filename), dtype=(S1dtype,[S1SizeX,S1SizeZ]))[0]
                mat_data['Spectral_apo'].append(data[S1ar_start:S1ar_end,:])
                mat_data['Spectral'].append(data[S1sr_start:S1sr_end,:])

            elif 'Spectral' in item.filename and not('Spectral0' in item.filename):
                data = np.frombuffer(zf.read(item.filename), dtype=(S1dtype,[S1SizeX,S1SizeZ]))[0]
                mat_data['Spectral'].append(data)

            elif 'Chirp' in item.filename:
                arr_type = mat_data['Header']['DataFileDict']['Chirp']['Type']
                SizeZ = int(mat_data['Header']['DataFileDict']['Chirp']['SizeZ'])
                bpp = int(mat_data['Header']['DataFileDict']['Chirp']['BytesPerPixel'])
                py_dtype = python_dtypes[arr_type][bpp]
                data = np.frombuffer(zf.read(item.filename),dtype=(py_dtype, SizeZ))
                mat_data['Chirp'] = data
            elif 'ApodizationSpectrum' in item.filename:
                arr_type = mat_data['Header']['DataFileDict']['ApodizationSpectrum']['Type']
                SizeZ = int(mat_data['Header']['DataFileDict']['ApodizationSpectrum']['SizeZ'])
                bpp = int(mat_data['Header']['DataFileDict']['ApodizationSpectrum']['BytesPerPixel'])
                py_dtype = python_dtypes[arr_type][bpp]
                data = np.frombuffer(zf.read(item.filename),dtype=(py_dtype, SizeZ))
                mat_data['ApodizationSpectrum'] = data
            elif 'OffsetErrors' in item.filename:
                arr_type = mat_data['Header']['DataFileDict']['OffsetErrors']['Type']
                SizeZ = int(mat_data['Header']['DataFileDict']['OffsetErrors']['SizeZ'])
                bpp = int(mat_data['Header']['DataFileDict']['OffsetErrors']['BytesPerPixel'])
                py_dtype = python_dtypes[arr_type][bpp]
                data = np.frombuffer(zf.read(item.filename),dtype=(py_dtype, SizeZ))
                mat_data['OffsetErrors'] = data

    from scipy.io.matlab import savemat
    savemat(re.split('\.[oO][cC][tT]',oct_filename)[0]+'.mat', mat_data)

    return mat_data


mat_data = OCTtoMATraw('test.oct') # see OCT_reader_demo.py to retrieve test.oct
