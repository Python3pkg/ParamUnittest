import unittest
import collections
import importlib


def _process_parameters(parameters_seq):
    processed_parameters_seq = []
    for parameters in parameters_seq:
        if isinstance(parameters, collections.Mapping):
            processed_parameters_seq.append((tuple(), dict(parameters)))
        elif (len(parameters) == 2
              and isinstance(parameters[0], collections.Sequence)
              and isinstance(parameters[1], collections.Mapping)):
            processed_parameters_seq.append((tuple(parameters[0]), dict(parameters[1])))
        else:
            processed_parameters_seq.append((tuple(parameters), dict()))
    return processed_parameters_seq


class ParametrizedTestCase(unittest.TestCase):
    def setParameters(self, *args, **kwargs):
        raise NotImplementedError('setParameters must be implemented because it receives the parameters.')


def parametrized(*parameters_seq):
    parameters_seq = _process_parameters(parameters_seq)
    def magic_module_set_test_case(cls):
        if not issubclass(cls, ParametrizedTestCase):
            raise TypeError('%s does not subclass %s' % (cls.__name__, ParametrizedTestCase.__name__))
        module = importlib.import_module(cls.__module__)
        for index, parameters in enumerate(parameters_seq):
            name = '%s_%d' % (cls.__name__, index)
            def closing_over(parameters=parameters):
                def setUp(self):
                    self.setParameters(*parameters[0], **parameters[1])
                    cls.setUp(self)
                return setUp
            set_up = closing_over()
            new_class = type(name, (cls, ), {'setUp': set_up})
            setattr(module, name, new_class)
        return None # this is explicit!
    return magic_module_set_test_case