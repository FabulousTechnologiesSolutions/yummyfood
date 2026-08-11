import factory

from apps.geo.models import City


class CityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = City
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'City {n}')
    is_active = True
