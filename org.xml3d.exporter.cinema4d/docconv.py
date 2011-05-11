################################################################################
#
#  docconv.py
#
#  Doxygen to __docstring__ conversion
#  Tab-to-space conversion
#
#  Copyright (C) 2010  Saarland University
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#  Author(s): Ken Patrik Dahm
#
################################################################################
import sys
import string
import os
import glob

tabSize = 4
convSuffix = '.converted.py'

def convertFile(src, dst):
    outsideClass = True
    outsideFunction = True
    comment = '"""\n'
    bufferArray = []
    for line in src:
        numTrailingWhitespaces = len(line) - len(string.lstrip(line))
        outsideClass = numTrailingWhitespaces == 0
        outsideFunction = numTrailingWhitespaces == tabSize

        hashIdx   = string.find(string.lstrip(line), '#')
        classIdx  = string.find(string.lstrip(line), 'class')
        funcIdx   = string.find(string.lstrip(line), 'def')
        paramCount  = string.count(line, '@param')
        returnCount = string.count(line, '@return')
        
        if classIdx == 0 or funcIdx == 0:
            trailingWhitespaces = ' ' * tabSize + ' ' * numTrailingWhitespaces
            dst.write(line)
            dst.write(trailingWhitespaces + comment)
            for cLine in bufferArray:
                stripped = string.lstrip(string.replace(cLine, '#', '', 1))
                dst.write(trailingWhitespaces + stripped)
            dst.write(trailingWhitespaces + comment)
            bufferArray = []
        elif hashIdx == 0 and (outsideFunction or outsideClass):
            modLine = line
            if paramCount != 0 or returnCount != 0:
                if string.count(line, ' -') != 0:
                    modLine = string.replace(line, ' -', ':', 1)
                elif paramCount != 0:
                    modLine = string.replace(line, '@param', '@param:', 1)
                elif returnCount != 0:
                    modLine = string.replace(line, '@return', '@return:', 1)
            bufferArray.append(modLine)			
        else:
            for commentLine in bufferArray:
                dst.write(commentLine)
            dst.write(line)
            bufferArray = []
            
def startConversion(srcFile):
    pyIdx = string.find(srcFile, '.py')
    if pyIdx == 0:
        return

    dstFile = srcFile + convSuffix
    print "Converting: %s. Writing converted to: %s" % (srcFile, dstFile)
    
    src = open(srcFile, 'r')
    dst = open(dstFile, 'w')
    
    convertFile(src, dst)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print "No directory given."
        print "Usage: python docconv.py --convert [root_directory file]+"
        print "Usage: python docconv.py --convertAndReplace [root_directory file]+"
        print "Usage: python docconv.py --clean"
    else:
        if sys.argv[1] == '--convert':		
            for i in xrange(2, len(sys.argv)):
                for subdir, dirs, files in os.walk(sys.argv[i]):
                    for file in files:
                        startConversion(os.path.join(subdir, file))
        elif sys.argv[1] == '--clean':
            for i in xrange(2, len(sys.argv)):
                for subdir, dirs, files in os.walk(sys.argv[i]):
                    for file in files:
                        convCount = string.count(file, convSuffix)
                        if convCount != 0:
                            os.remove(os.path.join(subdir, file))
        elif sys.argv[1] == '--convertAndReplace':
            for i in xrange(2, len(sys.argv)):
                for subdir, dirs, files in os.walk(sys.argv[i]):
                    for file in files:
                        # Convert file
                        fileName = os.path.join(subdir, file)
                        startConversion(fileName)
                        
                        # Replace and rename
                        convName = fileName + convSuffix
                        print "Remove: %s" % fileName
                        print "Rename %s to %s" % (convName, fileName)
                        os.remove(fileName)
                        os.rename(convName, fileName) 
        else:
            print "Invalid option."
            print "Usage: python docconv.py --convert [root_directory file]+"
            print "Usage: python docconv.py --convertAndReplace [root_directory file]+"
            print "Usage: python docconv.py --clean"

