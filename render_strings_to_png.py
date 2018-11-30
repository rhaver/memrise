# Requires ImageMagick to be installed (and included in the PATH environment variable)

import io
import os
import sys
import argparse
import json
import subprocess

def EscapeFileName(unsafeFileName):
	safeFileName = ''.join(c if c.isalnum() or c in ('_', '-') else '_' for c in unsafeFileName).strip()
	if 0 < len(safeFileName):
		return safeFileName
	else:
		raise Exception('Filename \'{0}\' not valid.'.format(unsafeFileName))

def EscapePango(unsafePangoString):
	return unsafePangoString.translate(str.maketrans({
		'&': r'&amp\;',
		'<': r'&lt\;',
		'>': r'&gt\;',
		'"': r'&quot\;',
		'\'': r'&apos\;',
		'\\': r'&#x5c\;',
		'%': r'&#x25\;'}))

def GeneratePngsWithPango(listCharSegments, strOutputDirectory, settings):
	'Takes a list with character segment objects and makes PNGs of them in the specified directory. Returns the total number of PNGs created.'
	counterPng = 0
	counterSeg = 0
	# go through all the character segment objects in the list that we got
	for charSegment in listCharSegments:
		# extract the character segment name
		name = charSegment['name']
		# go through all renditions of the character segment
		listRenditions = charSegment.get('renditions')
		print('\t{0}'.format(name))
		for i in range(0, len(listRenditions)):
			# set up the parameters necessary for calling ImageMagick
			fileName = '{0:03d}-{1}-{2}.png'.format(counterSeg + 1, EscapeFileName(name), i + 1) if 0 < i else '{0:03d}-{1}.png'.format(counterSeg + 1, EscapeFileName(name))
			font = listRenditions[i].get('font') or settings.get('defaultFont')
			renderString = listRenditions[i].get('pango') or EscapePango(listRenditions[i].get('utf8'))
			# generate a PNG using ImageMagick with Pango
			# (unfortunately it doesn't antialias so we first generate a too large image and then downsize it)
			subprocessArguments = ['magick', '-background', 'white', '-density', '600', settings['pango'].format(renderString, font), '-transparent', 'white', '-antialias', '-resize', '25%', '-trim', os.path.join(strOutputDirectory, fileName)]
			if listRenditions[i].get('pango-flip'):
				subprocessArguments.insert(-1, '-flip')
			if listRenditions[i].get('pango-flop'):
				subprocessArguments.insert(-1, '-flop')
			subprocess.run(subprocessArguments)
			counterPng += 1
		counterSeg += 1
	return counterPng

def EscapeXelatex(unsafeXelatexString):
	return unsafeXelatexString.translate(str.maketrans({
		'#': r'\#',
		'&': r'\&',
		'%': r'\%',
		'$': r'\$',
		'_': r'\_',
		'{': r'\{',
		'}': r'\}',
		'~': r'\textasciitilde{}',
		'^': r'\textasciicircum{}',
		'\\': r'\textbackslash{}',
		'"': r'\char"22'}))

def GeneratePngsWithXelatex(listCharSegments, strOutputDirectory, strWorkingDirectory, settings):
	'Takes a list with character segment objects and makes PNGs of them in the specified directory. Returns the total number of PNGs created.'
	counterPng = 0
	counterSeg = 0
	# go through all the character segment objects in the list that we got
	for charSegment in listCharSegments:
		# extract the character segment name
		name = charSegment['name']
		# go through all renditions of the character segment
		listRenditions = charSegment.get('renditions')
		print('\t{0}'.format(name))
		for i in range(0, len(listRenditions)):
			# set up the parameters necessary for calling XeLaTeX
			font = listRenditions[i].get('font') or settings.get('defaultFont')
			renderString = listRenditions[i].get('xelatex') or EscapeXelatex(listRenditions[i].get('utf8'))
			# generate a PDF in the working directory with XeLaTeX
			with subprocess.Popen(['xelatex', '-output-directory={0}'.format(strWorkingDirectory)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=False) as xelatex:
				xelatex.communicate(input=(settings['xelatex'].format(renderString, font)).encode('utf-8'))
			# set up the parameters necessary for calling ImageMagick
			fileName = '{0:03d}-{1}-{2}.png'.format(counterSeg + 1, EscapeFileName(name), i + 1) if 0 < i else '{0:03d}-{1}.png'.format(counterSeg + 1, EscapeFileName(name))
			# render the PDF to a PNG in the output directory using ImageMagick
			subprocess.run(['magick', '-antialias', '-density', '1200', os.path.join(strWorkingDirectory, 'texput.pdf'), '-trim', os.path.join(strOutputDirectory, fileName)])
			counterPng += 1
		counterSeg += 1
	return counterPng

def main():
	# setup STDOUT to accept UTF-8
	sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)
	# parse input arguments
	argParser = argparse.ArgumentParser(description='Generate PNGs of rendered characters with ImageMagick/Pango from a JSON specification.')
	argParser.add_argument('JsonSpecificationFile', type=argparse.FileType('r', encoding='utf8'), help='Input file with JSON specification.')
	argParser.add_argument('--engine', choices=['pango', 'xelatex'], required=True, help='What engine to use for rendering.')
	args = argParser.parse_args()
	# in windows: set working dir to be the location of the JSON file, if its the default
	if os.getcwd().lower() == 'c:\\windows\\system32':
		os.chdir(os.path.dirname(os.path.abspath(args.JsonSpecificationFile.name)))
	# open the JSON data and parse it
	with args.JsonSpecificationFile as f:
		jsonCharacterData = json.loads(f.read())
	settings = jsonCharacterData['settings']
	# set up an output directory and if necessary also a working directory
	dirOutput = '{0}-{1}-png'.format(EscapeFileName(settings.get('name')), args.engine) if settings.get('name') is not None else '{0}-png'.format(args.engine)
	dirCounter = -1
	while os.path.exists(dirOutput + str(dirCounter)):
		dirCounter -= 1
	dirOutput += str(dirCounter)
	os.makedirs(dirOutput)
	del(dirCounter)
	if args.engine == 'xelatex':
		dirWorking = os.path.join(dirOutput, 'tmp')
		os.makedirs(dirWorking)
	print('Output directory is \'{0}\'.'.format(os.path.abspath(dirOutput)))
	# generate PNGs
	counterTotalPng = 0
	characterSubsets = jsonCharacterData.get('subsets')
	if characterSubsets is not None:
		for subsetName, subsetListOfCharSegments in characterSubsets.items():
			# make a subdirectory
			subdir = os.path.join(dirOutput, EscapeFileName(subsetName))
			os.makedirs(subdir)
			# fetch the subset of character segments
			print('Processing {0} items in subset \'{1}\'...'.format(len(subsetListOfCharSegments), subsetName))
			# create the PNGs
			pngsCreated = {
				'pango':   lambda x: GeneratePngsWithPango(subsetListOfCharSegments, subdir, settings),
				'xelatex': lambda x: GeneratePngsWithXelatex(subsetListOfCharSegments, subdir, dirWorking, settings)
			}[args.engine](None)
			print('{0} PNGs created in \'{1}\''.format(pngsCreated, subdir))
			counterTotalPng += pngsCreated
	# remove working dir (if any) after removing all files in it
	if 'dirWorking' in locals():
		[os.remove(os.path.join(dirWorking, f)) for f in os.listdir(dirWorking)]
		os.rmdir(dirWorking)
	# done
	print('Done! {0} total PNGs written to {1}!'.format(counterTotalPng, dirOutput))

if __name__ == '__main__':
	main()