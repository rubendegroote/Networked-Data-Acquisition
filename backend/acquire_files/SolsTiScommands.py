# SolsTiS commands
import socket
IP = socket.gethostbyname(socket.gethostname())
import json
global transmission_id
transmission_id = 0

def give_message(operation, parameters):
    """Generates the message structure for transmitting to Solstis 2/3.

    Parameters
    ----------
    transmission_id: int
        Numerical identifier
    operation: str
        Name of the operation to be performed
    parameters: dict
        Dictionary of the parameter names and values"""
    global transmission_id
    transmission_id += 1
    return {
                     "message":
                     {
                        "transmission_id": [transmission_id],
                        "op": operation,
                        "parameters": parameters
                     }
            }

def start_link():
    """Links to the Solstis 2/3 server."""
    return give_message("start_link", {"ip_address": IP})

def ping():
    """Invert the case of received text and send it back."""
    return give_message("ping", {"text_in": "Test"})

def set_wave_m(wavelength):
    """This command instructs the SolsTiS to tune to the given wavelength.

    Parameters
    ----------
    wavelength: float
        Tuning value in nm within the tuning range of the SolsTiS."""
    return give_message("set_wave_m", {"wavelength": [wavelength]})

def poll_wave_m():
    """This command returns the status of the wavelength tuning software."""
    return give_message("poll_wave_m", {})

def lock_wave_m(status):
    """This command causes the wavelength lock to be applied or removed.

    Parameters
    ----------
    status: {'on', 'off'}"""
    return give_message("lock_wave_m", {"operation": status})

def stop_wave_m():
    """This command stops the currently active wavelength tuning operation."""
    return give_message("stop_wave_m", {})

def move_wave_t(wavelength):
    """This command instructs the SolsTiS to use the wavelength table only
    and tune the wavelength to the given value.

    Parameters
    ----------
    wavelength: float
        Tuning value in nm within the tuning range of the SolsTiS."""
    return give_message("move_wave_t", {"wavelength": [wavelength]})

def poll_move_wave_t():
    """This command returns the status of the most recently issued tune
    command."""
    return give_message("poll_move_wave_t", {})

def stop_move_wave_t():
    """This command stops the the most recently issued table tuning command."""
    return give_message("stop_move_wave_t", {})

def tune_etalon(setting):
    """This command adjusts the etalon tuning.

    Parameters
    ----------
    setting: float
        The etalon tuning range is expressed as a percentage
        where 100 is full scale."""
    return give_message("tune_etalon", {"setting": [setting]})

def tune_cavity(setting):
    """This command adjusts the reference cavity tuning.

    Parameters
    ----------
    setting: float
        The reference cavity tuning range is expressed as a percentage
        where 100 is full scale."""
    return give_message("tune_cavity", {"setting": [setting]})

def fine_tune_cavity(setting):
    """This command adjusts the reference cavity fine tuning.

    Parameters
    ----------
    setting: float
        Fine reference cavity tuning range is expressed as a percentage
        where 100 is full scale."""
    return give_message("fine_tune_cavity", {"setting": [setting]})

def tune_resonator(setting):
    """This command adjusts the resonator tuning.

    Parameters
    ----------
    setting: float
        The resonator tuning range is expressed as a percentage
        where 100 is full scale."""
    return give_message("tune_resonator", {"setting": [setting]})

def fine_tune_resonator(setting):
    """This command adjusts the resonator fine tuning.

    Parameters
    ----------
    setting: float
        The fine resonator tuning range is expressed as a percentage
        where 100 is full scale."""
    return give_message("fine_tune_resonator", {"setting": [setting]})

def etalon_lock(operation):
    """This command puts the etalon lock on or off.

    Parameters
    ----------
    operation: {'on', 'off'}"""
    return give_message("etalon_lock", {"operation": operation})

def etalon_lock_status():
    """This command gets the current status of the etalon lock."""
    return give_message("etalon_lock_status", {})

def cavity_lock(operation):
    """This command puts the reference cavity lock on or off.

    Parameters
    ----------
    operation: {'on', 'off'}"""
    return give_message("cavity_lock", {"operation": operation})

def cavity_lock_status():
    """This command gets the current status of the reference cavity lock."""
    return give_message("cavity_lock_status", {})

def ecd_lock(operation):
    """This command puts the ECD lock on or off.

    Parameters
    ----------
    operation: {'on', 'off'}"""
    return give_message("ecd_lock", {"operation": operation})

def ecd_lock_status():
    """This command gets the current status of the ECD lock."""
    return give_message("ecd_lock_status", {})

def monitor_a(signal):
    """This command switches the requested signal to monitor A output port.

    Parameters
    ----------
    signal: int
        Requested signal:
        1 - Etalon dither.
        2 - Etalon voltage.
        3 - ECD slow voltage.
        4 - Reference cavity.
        5 - Resonator fast V.
        6 - Resonator slow V.
        7 - Aux output PD.
        8 - Etalon error.
        9 - ECD error.
        10 - ECD PD1
        11 - ECD PD2.
        12 - Input PD.
        13 - Reference cavity PD.
        14 - Resonator error
        15 - Etalon PD AC
        16 - Output_PD"""
    return give_message("monitor_a", {"signal": [signal]})

def monitor_b(signal):
    """This command switches the requested signal to monitor B output port.

    Parameters
    ----------
    signal: int
        Requested signal:
        1 - Etalon dither.
        2 - Etalon voltage.
        3 - ECD slow voltage.
        4 - Reference cavity.
        5 - Resonator fast V.
        6 - Resonator slow V.
        7 - Aux output PD.
        8 - Etalon error.
        9 - ECD error.
        10 - ECD PD1
        11 - ECD PD2.
        12 - Input PD.
        13 - Reference cavity PD.
        14 - Resonator error
        15 - Etalon PD AC
        16 - Output_PD"""
    return give_message("monitor_b", {"signal": [signal]})

def select_profile(profile):
    """This command selects an etalon profile.

    Parameters
    ----------
    profile: int (1 to 5)
        Each system transmission_id, can have up to 5 defined rofiles."""
    return give_message("select_profile", {"profile": [profile]})

def get_status():
    """This command obtains the current system status."""
    return give_message("get_status", {})

def get_alignment_status():
    """This command obtains the current beam alignment status."""
    return give_message("get_alignment_status", {})

def beam_alignment(mode):
    """This command controls the operation of the beam alignment.

    Parameters
    ----------
    mode: int (1 to 3)
        1 - Manual
        2 - Automatic
        3 - Stop (and hold current values"""
    return give_message("beam_alignment", {"mode": [mode]})

def beam_adjust_x(x_value):
    """Adjusts the x alignment in beam alignment operations.

    Parameters
    ----------
    x_value: float
        X alignment percentage value, centre = 50"""
    return give_message("beam_adjust_x", {"x_value": [x_value]})

def beam_adjust_y(y_value):
    """Adjusts the y alignment in beam alignment operations.

    Parameters
    ----------
    y_value: float
        Y alignment percentage value, centre = 50"""
    return give_message("beam_adjust_y", {"y_value": [y_value]})

def scan_stitch_initialise(scan, start, stop, rate, units):
    """This command initialises the scan stitching operations on Solstis.

    Parameters
    ----------
    scan: {'coarse', 'medium', 'fine', 'line'}
        "coarse" - BRF only, not currently available.
        "medium" - BRF + etalon tuning.
        "fine" - BRF + etalon + resonator tuning.
        "line" - Line narrow scan, BRF + etalon + cavity tuning.
    start: float
        650-1100 Scan start position in nm.
    stop: float
        650-1100 Scan stop position in nm.
    rate: int
        Scan speed, selected in conjunction with units
        Medium scan, units = GHz/s
            100, 50, 20, 15, 10, 5, 2, 1.
        Fine scan and line narrow scan, units = GHz/s
            20, 10, 5, 2, 1.
        Fine scan and line narrow scan, units = MHz/s
            500, 200, 100, 50, 20, 10, 5, 2, 1.
        Line narrow scan, units = kHz/s
            500, 200, 100, 50.
    unit: {'GHz/s', 'MHz/s', 'kHz/s'}
    """
    return give_message("scan_stitch_initialise", {
                                                        "scan": scan,
                                                        "start": [start],
                                                        "stop": [stop],
                                                        "rate": [rate],
                                                        "units": [units]
                                                        }
                        )

def scan_stitch_op(scan, operation):
    """This command controls the scan stitching operations on Solstis.

    Parameters
    ----------
    scan: {'coarse', 'medium', 'fine', 'line'}
    operation: {'start', 'stop'}
        start - Start running the given scan.
        stop - Stop running the given scan."""
    return give_message("scan_stitch_op", {"scan": scan,
                                                            "operation": operation})

def scan_stitch_status(scan):
    """This command obtains the status of the scan stitching operations
    on Solstis.

    Parameters
    ----------
    scan: {'coarse', 'medium', 'fine', 'line'}"""
    return give_message("scan_stitch_status", {"scan": scan})

def scan_stitch_output(operation, update):
    """Scan stitching operations can be configured to transmit the current
    wavelength to a Client system while they are running. This command turns
    this feature on or off. The message is generated at the beginning and
    end of each scan stage and may also be generated during the scan, see
    "update" field below.

    Parameters
    ----------
    operation: {'start', 'stop'}
    update: float
        0.1 -- 50.0 - Additional update messages will be generated
        as the tuning is increased by this amount during the ramp phase."""
    return give_message("scan_stitch_output", {"operation": operation,
                                                                "update": [update]})

def fast_scan_start(scan, width, time):
    """This command allows the remote interface to use the fast scans
    similar to those on the control page of the SolsTiS. There are 8
    possible scan options which operate on the Reference Cavity,
    Resonator and ECD tuning controls. The currently tuned value is
    taken to be the centre of the scan and the command is called with a
    scan width and time. The start point of the scan is
    (centre – (0.5 * scan width)). The end of the scan is
    (centre + (0.5 * scan width)). The tuning output is ramped from the
    start point to the end point in the time given.

    Parameters
    ----------
    scan: {"cavity_continuous", "cavity_single", "resonator_continuous",
    resonator_single", "ecd_continuous", "fringe_test", "resonator_ramp",
    "ecd_ramp", "cavity_triangular", "resonator_triangular"}
        Each of the 8 scans is selected with a string similar to that on the
        selection list on the Control page. The following list also shows the
        tuning control whose value is ramped by the selected scan.
            "cavity_continuous" - Reference Cavity
            "cavity_single" - Reference Cavity
            "resonator_continuous" - Resonator
            "resonator_single" - Resonator
            "ecd_continuous" - ECD
            "fringe_test" - Reference Cavity
            "resonator_ramp" - Resonator
            "ecd_ramp" - ECD
            "cavity_triangular" - Reference Cavity
            "resonator_triangular" - Resonator
    width: float
        The scan is specified in GHz and has a low limit of 0.01. The
        upper limit depends on the capabilities of the tuning control.
        A typical set of maximum scan widths would be as follows:
            Reference Cavity 130 GHz
            Resonator 30 GHz
            ECD 100 GHz
        A further complication with scan widths is that the full scan
        width can only be achieved if the tuning control is at its
        centre value. A failed status value of 1 shall be returned
        if the requested scan width is not possible.
    time: float (0.01 to 10000)
        Duration of the scan in seconds. If the time is too short
        for the given width the system will ramp the tuner run as fast as
        it can."""
    return give_message("fast_scan_start", {"scan": scan,
                                                             "width": [width],
                                                             "time": [time]})

def fast_scan_poll(scan):
    """This command polls fast scans.

    Parameters
    ----------
    scan: {"cavity_continuous", "cavity_single", "resonator_continuous",
    resonator_single", "ecd_continuous", "fringe_test", "resonator_ramp",
    "ecd_ramp", "cavity_triangular", "resonator_triangular"}"""
    return give_message("fast_scan_poll", {"scan": scan})

def fast_scan_stop(scan):
    """This command stops the fast scans. The tuning DAC is returned to
    its start position.

    Parameters
    ----------
    scan: {"cavity_continuous", "cavity_single", "resonator_continuous",
    resonator_single", "ecd_continuous", "fringe_test", "resonator_ramp",
    "ecd_ramp", "cavity_triangular", "resonator_triangular"}"""
    return give_message("fast_scan_stop", {"scan": scan})

def fast_scan_stop_nr(scan):
    """This command stops the fast scans. The tuning value is NOT returned
    to its start position. This command is not available for ECD operations
    which always return to the tuner start position.

    Parameters
    ----------
    scan: {"cavity_continuous", "cavity_single", "resonator_continuous",
    resonator_single", "ecd_continuous", "fringe_test", "resonator_ramp",
    "ecd_ramp", "cavity_triangular", "resonator_triangular"}"""
    return give_message("fast_scan_stop_nr", {"scan": scan})