import requests

from invoices.distancematrix import DistanceMatrix


def create_distance_matrix(location_dict, api_key):
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    distance_matrix = {}
    duration_matrix = {}
    # build a list of addresses but keep patient id as key
    addresses_dict = {custom_id: location_dict[custom_id] for custom_id in location_dict.keys()}

    # loop over the addresses_dict to build the distance matrix
    for o in addresses_dict.keys():
        for d in addresses_dict.keys():
            if o == d:
                # Distance to the same location is zero
                distance_matrix[o] = {}
                distance_matrix[o][d] = 0
            else:
                params = {
                    'origins': addresses_dict[o],
                    'destinations': addresses_dict[d],
                    'key': api_key,
                    'mode': 'driving',
                    'language': 'en-EN',
                    'units': 'metric'
                }
                response = requests.get(url, params=params)
                result = response.json()
                if result['status'] != 'OK':
                    raise Exception(result['error_message'])
                distance = result['rows'][0]['elements'][0]['distance']['text']
                duration = result['rows'][0]['elements'][0]['duration']['text']
                # convert distance to integer knowing that the distance is in km and looks like that '35.0 km'
                distance = int(float(distance.split(' ')[0]))
                # convert duration to integer
                duration = int(duration.split(' ')[0])
                distance_matrix[o] = {}
                distance_matrix[o][d] = distance
                duration_matrix[o] = {}
                duration_matrix[o][d] = duration
                print(o, d, distance, duration)
                # If a distance matrix already exists, either for the same origin and destination or the reverse
                # then take the next one
                dmatrix = DistanceMatrix.objects.create(
                    patient_origin=o,
                    patient_destination=d,
                    distance_in_km=distance,
                    duration_in_mn=duration
                )
                dmatrix.save()


    return distance_matrix

# Example usage
#locations = ['XX', 'YY', 'ZZ']
# matrix = create_distance_matrix(locations, api_key)
