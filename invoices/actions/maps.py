import json

import requests
from constance import config
from django.http import HttpResponse


def calculate_distance_matrix(modeladmin, request, queryset):
    headers = {
        'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
        'Authorization': config.OPENROUTE_SERVICE_API_KEY
    }

    url_address = "https://api.openrouteservice.org/v2/matrix/driving-car?api_key"

    r = requests.post(url=url_address, headers=headers,
                      # bureau, b, d, n, r, w, z, f, t, W
                      json={"locations": [[6.08753, 49.60005],
                                          [6.10284, 49.61556],
                                          [6.11577, 49.6152],
                                          [6.12931, 49.61408],
                                          [6.05086, 49.60906],
                                          [6.21873, 49.70394],
                                          [6.14958, 49.56788],
                                          [6.22188, 49.5874],
                                          [6.21597, 49.61536],
                                          [6.1207, 49.67666]],
                            "metrics": ["duration"],
                            "units": "km"})
    data = json.loads(r.text)
    # {'durations': [[0.0, 344.48, 485.28, 570.03, 522.45, 1524.1, 802.08, 937.8, 855.35, 1041.85],
    #                [352.3, 0.0, 164.16, 413.78, 572.16, 1383.33, 828.76, 964.48, 882.03, 793.69],
    #                [473.44, 164.16, 0.0, 314.4, 736.27, 1317.73, 827.57, 1095.02, 1012.57, 728.09],
    #                [515.77, 277.26, 176.61, 0.0, 796.04, 1126.29, 825.91, 962.38, 879.93, 800.59],
    #                [526.38, 618.59, 769.48, 854.23, 0.0, 1665.66, 946.75, 1082.47, 1000.02, 1074.05],
    #                [1486.05, 1317.26, 1216.6, 1132.78, 1611.08, 0.0, 1415.4, 1190.2, 1107.75, 912.73],
    #                [847.26, 849.91, 877.19, 793.36, 972.3, 1523.51, 0.0, 594.27, 643.7, 1409.09],
    #                [1011.04, 1013.69, 1025.15, 944.87, 1136.07, 1201.97, 601.14, 0.0, 315.95, 1267.44],
    #                [930.4, 933.04, 944.5, 864.22, 1055.43, 1121.32, 641.0, 318.96, 0.0, 1186.8],
    #                [1085.78, 825.36, 748.41, 804.73, 1078.52, 912.73, 1394.76, 1231.28, 1148.83, 0.0]],
    #  'destinations': [{'location': [6.087722, 49.600007], 'snapped_distance': 14.66},
    #                   {'location': [6.102926, 49.615809], 'snapped_distance': 28.37},
    #                   {'location': [6.115879, 49.615288], 'snapped_distance': 12.59},
    #                   {'location': [6.129109, 49.61404], 'snapped_distance': 15.12},
    #                   {'location': [6.050846, 49.609142], 'snapped_distance': 9.14},
    #                   {'location': [6.218567, 49.703891], 'snapped_distance': 12.94},
    #                   {'location': [6.149445, 49.567844], 'snapped_distance': 10.52},
    #                   {'location': [6.221691, 49.587249], 'snapped_distance': 21.58},
    #                   {'location': [6.215769, 49.615304], 'snapped_distance': 15.78},
    #                   {'location': [6.120666, 49.676563], 'snapped_distance': 11.02}],
    #  'sources': [{'location': [6.087722, 49.600007], 'snapped_distance': 14.66},
    #              {'location': [6.102926, 49.615809], 'snapped_distance': 28.37},
    #              {'location': [6.115879, 49.615288], 'snapped_distance': 12.59},
    #              {'location': [6.129109, 49.61404], 'snapped_distance': 15.12},
    #              {'location': [6.050846, 49.609142], 'snapped_distance': 9.14},
    #              {'location': [6.218567, 49.703891], 'snapped_distance: 12.94},
    #              {'location': [6.149445, 49.567844], 'snapped_distance': 10.52},
    #              {'location': [6.221691, 49.587249], 'snapped_distance': 21.58},
    #              {'location': [6.215769, 49.615304], 'snapped_distance': 15.78},
    #              {'location': [6.120666, 49.676563], 'snapped_distance': 11.02}],
    #  'metadata': {'attribution': 'openrouteservice.org | OpenStreetMap contributors', 'service': 'matrix',
    #               'timestamp': 1664541443290, 'query': {
    #          'locations': [[6.08753, 49.60005], [6.10284, 49.61556], [6.11577, 49.6152], [6.12931, 49.61408],
    #                        [6.05086, 49.60906], [6.21873, 49.70394], [6.14958, 49.56788], [6.22188, 49.5874],
    #                        [6.21597, 49.61536], [6.1207, 49.67666]], 'profile': 'driving-car', 'responseType': 'json',
    #          'metricsStrings': ['DURATION'], 'metrics': ['duration'], 'units': 'km'},
    #               'engine': {'version': '6.7.0', 'build_date': '2022-02-18T19:37:41Z',
    #                          'graph_date': '2022-09-18T14:35:47Z'}}}
    response = HttpResponse(r, content_type="application/json")

    return response
