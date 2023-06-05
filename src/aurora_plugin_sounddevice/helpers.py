import sounddevice as sd


def get_samplerate_func(type_: str):

    def get_samplerate(v, values):
        if not v:
            info = sd.query_devices(values["device"], type_)
            v = int(info["default_samplerate"])
        return v

    return get_samplerate
