from constance import config

from invoices import settings


def get_settings(allow_settings):
    setting_list = []
    for key, options in getattr(settings, 'CONSTANCE_CONFIG', {}).items():
        if key in allow_settings:
            default, help_text = options[0], options[1]
            data = {'key': key,
                    'default': default,
                    'help_text': help_text,
                    'value': getattr(config, key)}
            setting_list.append(data)
    return setting_list
