import yaml
import re
import math

treeInfoDistance = 7


class configurations(object):
    """Parses and searches the static serve configuration."""

    def __init__(self, raw):
        super(configurations, self).__init__()
        self.raw = self._dataModelWith(raw)

    # ######## External Methods ######## #
    def infoForPathItems(self, pathItems):
        if not isinstance(pathItems, list):
            raise ValueError('pathItems Must be an array!')
            return

        # Maintain our position so we know what path we actually need to grab
        mList = list(pathItems)

        # Set the current node to the root node
        info = {}
        currentNode = (self.raw['paths'], {})
        pathItems.append('')
        for component in pathItems:

            # Inherit attributes of current node
            for key in self._infoKeysToInherit():
                if key not in currentNode[1]:
                    continue

                # Remove the current item from My Account mutable list if navigation key was
                # updated
                if key in self._infoNavigationKeys():
                    del mList[0]
                    # Remove all other navigation keys
                    for nKey in self._infoNavigationKeys():
                        if nKey not in info:
                            continue
                        del info[nKey]

                # Update our info key
                info[key] = currentNode[1][key]

            # Stop if there are no more components.
            if component not in currentNode[0]:
                break

            # Get the new node
            currentNode = currentNode[0][component]

        # Report Info, and non-traversed items
        return (info, mList)

    def renderTree(self, tab=0, branch=0):
        cBranch = self.raw['paths']
        # If branch was set override cBranch with inputted branch
        if not branch == 0:
            cBranch = branch

        # Store the tab string
        tabs = '   ' * tab
        if not tab == 0:
            tabs = tabs + '|--'

        for component in cBranch:
            # Add Tabs And component name
            bstr = tabs + component

            # Add post component tabs to align component info. where 8 tabs is
            # the system tab count
            tabCount = math.floor(treeInfoDistance - (len(bstr)/8))
            bstr = bstr + ("\t" * tabCount)

            # print the generated string with the branch info.
            print (bstr + str(cBranch[component][1]))

            # render sub route 1 tab in
            self.renderTree(tab=(tab + 1), branch=cBranch[component][0])

        # If we are the root caller the add a newline.
        if tab == 0:
            print ("")

    # ######## Internal Methods ######## #

    def _infoKeysToInherit(self):
        return ['basePrice', 'localPath', 'proxyPass', 'priceMode']

    def _infoNavigationKeys(self):
        return ['localPath', 'proxyPass']

    # Converts the inputted data model into a traversable tree
    def _dataModelWith(self, raw):
        if not isinstance(raw, str):
            raise ValueError('raw Must be a string!')
            return

        # Normalize and convert
        configObj = yaml.load(self._normilizeConfiguration(raw))
        if not isinstance(raw, object):
            raise ValueError('Failed to parse configuration!')
            return

        # make a copy
        copy = configObj.copy()

        # convert paths and set
        extractedPaths = self._extractPathData(configObj['paths'])
        copy['paths'] = self._compositeTupleListToTree(extractedPaths)

        # Set to raw
        return copy

    # Normalize chars in the yaml
    def _normilizeConfiguration(self, configString):
        rep = {"\t": "    "}
        rep = dict((re.escape(k), v) for k, v in rep.items())
        pattern = re.compile("|".join(rep.keys()))
        return pattern.sub(lambda m: rep[re.escape(m.group(0))], configString)

    # Converts the paths in to arrays
    def _extractPathData(self, paths):
        extractedPaths = []
        for path in paths:
            lPath = path.split('/')
            del lPath[0]
            # append path data also
            extractedPaths.append((lPath, paths[path]))

        return extractedPaths

    # Converts tuples with path arrays into a tree.
    def _compositeTupleListToTree(self, tList):
        tempList = list(tList)

        # Sort List From least descriptive to most descriptive
        tempList.sort(key=lambda val: len(val[0]))

        # Add the Items to the map using the path
        orgObj = {}
        currentName = ''

        for item in tempList:
            # Stop at the end of the branch
            if len(item[0]) == 0:
                continue

            # Get the current base path
            currentName = item[0][0]
            del item[0][0]

            # Ensure we have a list
            if currentName not in orgObj:
                orgObj[currentName] = []

            # Add the Item to the list
            orgObj[currentName].append(item)

        # print orgObj["public"];
        for key in orgObj:
            ret = self._compositeTupleListToTree(orgObj[key])

            # We are at the end of the branch convert to a tuple
            # Set the resulting dictionary to the first index forming a
            # (components, info) tuple.
            orgObj[key] = (ret, orgObj[key][0][1])

        return orgObj
