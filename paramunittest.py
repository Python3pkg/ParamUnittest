# Copyright 2012 Enrico Franchi
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import copy
import unittest
import collections
import importlib

__all__ = [
    'parametrized',
    'ParametrizedTestCase',
]

def _process_parameters(parameters_seq):
    processed_parameters_seq = []
    for parameters in parameters_seq:
        if isinstance(parameters, collections.Mapping):
            processed_parameters_seq.append((tuple(),
                                             dict(parameters)))
        elif (len(parameters) == 2
              and isinstance(parameters[0], collections.Sequence)
              and isinstance(parameters[1], collections.Mapping)):
            processed_parameters_seq.append((tuple(parameters[0]),
                                             dict(parameters[1])))
        else:
            processed_parameters_seq.append((tuple(parameters),
                                             dict()))
    return processed_parameters_seq


def _build_name(name, index):
    return '%s_%d' % (name, index)


def strclass(cls):
    return "%s.%s" % (cls.__module__, cls.__name__)


class ParametrizedTestCase(unittest.TestCase):
    def setParameters(self, *args, **kwargs):
        raise NotImplementedError(
            ('setParameters must be implemented '
             'because it receives the parameters.'))

    def getParameters(self):
        """
        Return the parameters with which this test case was instantiated.
        """
        raise NotImplementedError(
            'getParameters should have been patched by parametrized.')

    def getFullParametersSequence(self):
        raise NotImplementedError(
            'getFullParametersSequence should have been patched by parametrized.')

    def getTestCaseIndex(self):
        """
        Return the index of the current test case according to the list of
        parametes passed to parametrized.
        """
        raise NotImplementedError(
            'getTestCaseIndex should have been patched by parametrized.')

    def getFullParametersSequence(self):
        """
        Return the full normalized list of parameters passed to parametrized.
        """
        raise NotImplementedError(
            'getFullParametersSequence should have been patched by parametrized.')

    def __str__(self):
        try:
            return "%s[%d](%s) (%s)" % (self._testMethodName,
                                        self.getTestCaseIndex(),
                                        self.getParameters(),
                                        strclass(self.__class__))
        except NotImplementedError:
            return "%s[...](...) (%s)" % (self._testMethodName,
                                        strclass(self.__class__))

    def __repr__(self):
        try:
            return "<%s[%d](%s) testMethod=%s>" % (strclass(self.__class__),
                                                   self.getTestCaseIndex(),
                                                   self.getParameters(),
                                                   self._testMethodName)
        except NotImplementedError:
            return "<%s[...](...) testMethod=%s>" % (strclass(self.__class__),
                                                   self._testMethodName)




class PropagateSetAttr(type):
    def __new__(mcs, name, bases, dct):
        dct['setattr_observers'] = []
        cls = super(PropagateSetAttr, mcs).__new__(mcs, name, bases, dct)
        return cls

    def __setattr__(cls, key, value):
        for observer in cls.setattr_observers:
            setattr(observer, key, value)



def make_propagator(cls, setattr_observers):
    SkippableTest = PropagateSetAttr('SkippableTest', (unittest.TestCase,),
                                     {})
    SkippableTest.setattr_observers.extend(setattr_observers)
    return SkippableTest


def parametrized(*parameters_seq):
    parameters_seq = _process_parameters(parameters_seq)
    def magic_module_set_test_case(cls):
        if not hasattr(cls, 'setParameters'):
            raise TypeError('%s does not have a setParameters method.' % (
                cls.__name__, ))
        module = importlib.import_module(cls.__module__)
        generated_test_cases = []
        for index, parameters in enumerate(parameters_seq):
            name = _build_name(cls.__name__, index)
            def closing_over(parameters=parameters, index=index):
                def setUp(self):
                    self.setParameters(*parameters[0], **parameters[1])
                    cls.setUp(self)
                def getParameters(self):
                    """
                    Return the parameters with which this test case was instantiated.
                    """
                    return parameters
                def getTestCaseIndex(self):
                    """
                    Return the index of the current test case according to the list of
                    parametes passed to parametrized.
                    """
                    return index
                def getFullParametersSequence(self):
                    """
                    Return the full normalized list of parameters passed to parametrized.
                    """
                    return copy.copy(parameters_seq)
                return setUp, getParameters, getTestCaseIndex, getFullParametersSequence
            (set_up, get_parameters,
             get_test_case_index,
             get_full_parameters_sequence) = closing_over()
            new_class = type(name, (cls, ),
                             {'setUp': set_up,
                              'getParameters': get_parameters,
                              'getTestCaseIndex': get_test_case_index,
                              'getFullParametersSequence': get_full_parameters_sequence})
            generated_test_cases.append(new_class)
            setattr(module, name, new_class)
        return make_propagator(cls, generated_test_cases)
    return magic_module_set_test_case
