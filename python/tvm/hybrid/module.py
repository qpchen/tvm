"""Methods and data structures to support dumping HalideIR to Hybrid Script.
This allows users to do quick hack to generated HalideIR and cast it back to
TVM modules.

To enable this feature, you need to build with -DUSE_HYBRID_DUMP=ON.
"""

import ast
import imp

from ..contrib import util
from .util import _internal_assert
from .util import _is_tvm_arg_types
from .parser import source_to_op


class HybridModule(object):
    """The usage of Hybrid Module is very similar to conventional TVM module,
    but conventional TVM module requires a function body which is already fully
    lowered. This contradicts to the fact that Hybrid Module is originally a text
    format for Phase 0 HalideIR. Thus, a totally separated module is defined."""


    def __init__(self, src=None, name=None):
        """The constructor of this a hybrid module

        Parameters
        ----------
        src : str
            The source code of this module

        name : str
            The name of this module
        """
        self.src_ = self.name = self.func_ = self.root_ = None
        if src is not None:
            temp = util.tempdir()
            dst = temp.relpath("script.py")
            with open(dst, 'w') as f:
                f.write("import tvm\n@tvm.hybrid.script\n%s" % src)

            if name is not None:
                self.name = name
            self.load(dst)


    def __call__(self, *args):
        if _is_tvm_arg_types(args):
            return source_to_op(self.root_, globals(), args)
        return self.func_(*args)


    def get_source(self):
        return self.src_


    def save(self, path):
        if not path.endswith('.py'):
            path = path + '.py'
        with open(path, 'w') as f:
            f.write(self.src_)


    def load(self, path):
        """Load the module from a python file

        Parameters
        ----------
        path : str
            Path to the given python file
        """
        with open(path, 'r') as f:
            self.src_ = f.read()

        src = self.src_

        class FindFunc(ast.NodeVisitor):
            """ Find the function in module to be loaded module. """
            #pylint: disable=invalid-name
            def __init__(self):
                self.name = None
                self.root = None


            def visit_FunctionDef(self, node):
                _internal_assert(self.name is None, "For now, only one function supported!")
                self.name = node.name
                _internal_assert(self.root is None, "For now, only one function supported!")
                self.root = node

        root = ast.parse(src)
        finder = FindFunc()
        finder.visit(root)
        _internal_assert(finder.name is not None and finder.root is not None, \
                         "No function found!")
        if self.name is None:
            self.name = finder.name
        self.root_ = finder.root
        py_module = imp.load_source(self.name, path)
        self.func_ = getattr(py_module, self.name)
