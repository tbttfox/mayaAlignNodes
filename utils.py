import os
import sys
from .Qt.QtCore import QObject, QTimer
from .Qt.QtGui import QIcon


def getUiFile(fileVar, subFolder="ui", uiName=None):
    """Get the path to the .ui file

    Parameters
    ----------
    fileVar : str
            The __file__ variable passed from the invocation
    subFolder : str
            The folder to look in for the ui files. Defaults to 'ui'
    uiName : str or None
            The name of the .ui file. Defaults to the basename of
            fileVar with .ui instead of .py

    Returns
    -------
    str
            The path to the .ui file

    """
    uiFolder, filename = os.path.split(fileVar)
    if uiName is None:
        uiName = os.path.splitext(filename)[0]
    if subFolder:
        uiFile = os.path.join(uiFolder, subFolder, uiName + ".ui")
    return uiFile


def clearPathSymbols(paths, keepers=None):
    """Removes path symbols from the environment.

    This means I can unload my tools from the current process and re-import them
    rather than dealing with the always finicky reload()

    We use directory paths rather than module names because it gives us more control
    over what is unloaded

    Parameters
    ----------
    paths : list
            List of directory paths that will have their modules removed
    keepers : list or None
            List of module names that will not be removed (Default value = None)
    """
    keepers = keepers or []
    paths = [os.path.normcase(os.path.normpath(p)) for p in paths]

    for key, value in sys.modules.items():
        protected = False

        # Used by multiprocessing library, don't remove this.
        if key == "__parents_main__":
            protected = True

        # Protect submodules of protected packages
        if key in keepers:
            protected = True

        ckey = key
        while not protected and "." in ckey:
            ckey = ckey.rsplit(".", 1)[0]
            if ckey in keepers:
                protected = True

        if protected:
            continue

        try:
            packPath = value.__file__
        except AttributeError:
            continue

        packPath = os.path.normcase(os.path.normpath(packPath))

        isEnvPackage = any(packPath.startswith(p) for p in paths)
        if isEnvPackage:
            sys.modules.pop(key)
