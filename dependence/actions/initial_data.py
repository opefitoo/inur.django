import json

from dependence.longtermcareitem import LongTermCareItem


def create_or_update_long_term_item_based_on_fixture(self, request, queryset):
    # load the fixture file
    fixture = open('dependence/fixtures/longtermitems.json', 'r')
    fixture_data = json.load(fixture)
    fixture.close()
    # loop through the fixture data
    for data in fixture_data:
        if LongTermCareItem.objects.filter(code=data['fields']['code']).exists():
            # update
            item = LongTermCareItem.objects.get(code=data['fields']['code'])
            item.short_description = data['fields']['short_description']
            # checks if description key exists
            if 'description' in data['fields'] and data['fields']['description'] is not None:
                item.description += "\n %s" % data['fields']['description']
            item.weekly_package = data['fields']['weekly_package']
            item.save()
            print('Updated item: ' + item.code)
        else:
            # create
            item = LongTermCareItem.objects.create(code=data['fields']['code'],
                                                   short_description=data['fields']['short_description'],
                                                   # set description if it exists
                                                   description=data['fields']['description'] if 'description' in data[
                                                       'fields'] and data['fields']['description'] is not None else '',
                                                   weekly_package=data['fields']['weekly_package'])
            item.save()
            print('Created item: ' + item.code)
