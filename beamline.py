from math import ceil
from astropy import units as u

from instrument import Instrument

def memory_requirement(num_pixel, num_event, num_core):
    # Assumptions:
    # - Each core (MPI rank) requires a baseline of 1 GB.
    # - The Instrument takes 256 Byte/pixel/core, but is assumed to be shared between workspaces.
    # - We require 5 workspaces.
    base_mem = 2**30 * u.byte
    mem_per_pixel = 256 * u.byte
    num_workspace = 5
    num_bin = 1000
    # TODO Include memory for meta-data?
    return num_core*(base_mem + mem_per_pixel * num_pixel) + num_workspace*(num_pixel * num_bin * 3 * 8 * u.byte + num_event * 2 * 8 * u.byte)

class Beamline:
    def __init__(self, name):
        self.name = name
        self.phases = []
        self.configs = []

    def add_phase(self, num_pixel):
        self.phases.append(num_pixel)

    def add_config(self, name, event_rate, event_count):
        self.configs.append((name, event_rate, event_count))

    def run(self, accelerator_power, speedup):
        for name, rate, count in self.configs:
            for phase_id, phase in enumerate(self.phases):
                assert phase <= self.phases[-1] # phases must be ordered, highest pixel count last
                for power in accelerator_power:
                    reduced_rate = rate*power/5.0*phase/self.phases[-1]
                    run_duration = count/reduced_rate
                    # Typically we have to process a sample run together with a background run.
                    # For now we assume that both have similar size, i.e., the effective number of
                    # events in the reduction is twice that of the run:
                    sample_and_background = 1 + 1
                    i = Instrument(phase, sample_and_background*reduced_rate, run_duration)
                    output = '{:4.1f} MW {:6} {:7} pixels {:30} {:6.0} n/s {:6.0f} run[s]'.format(power, self.name, phase, name, reduced_rate.value, run_duration.value)
                    reduction_duration = min(max(run_duration/speedup, 30 * u.second), 1200 * u.second)
                    resources = i.required_resources(reduction_duration)
                    # Average cores takes into account reducing data several times.
                    reductions_per_run = 2
                    # TODO take into account that not 100% of time is measurement time?
                    cores = resources['cores']
                    try:
                        output += ' {:6.0f} reduction[s] {:3} cores {:4.0f} average-cores'.format(reduction_duration.value, cores, ceil(reductions_per_run*(reduction_duration/run_duration)*cores))
                        output += ' {:4.0f} GByte/core'.format(ceil(memory_requirement(phase, reduced_rate*run_duration, cores).value/2**30/cores))
                    except:
                        output += ' {:6.0f} reduction[s] {:3} cores {:4} average-cores'.format(reduction_duration.value, cores, ' inf')
                    print(output)
