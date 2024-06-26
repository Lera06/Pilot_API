from django.shortcuts import render

from rest_framework import generics
from rest_framework.response import Response
from rest_framework.reverse import reverse
from django_filters import AllValuesFilter, DateTimeFilter, NumberFilter
from django_filters import rest_framework as filters

from drones.models import (DroneCategory,
                           Drone,
                           Pilot,
                           Competition)
from drones.serializers import (DroneCategorySerializer,
                                DroneSerializer,
                                PilotSerializer,
                                PilotCompetitionSerializer)
from rest_framework import permissions
from rest_framework.throttling import ScopedRateThrottle
from .custompermission import IsCurrentUserOwnerOrReadOnly


class DroneCategoryList(generics.ListCreateAPIView):
    queryset = DroneCategory.objects.all()
    serializer_class = DroneCategorySerializer
    name = 'dronecategory-list'

    filter_fields = (
        'name',
                     )
    search_fields = (
        '^name',                  # http ":8000/drone-categories/?search=Quadcopter"
    )                             # http ":8000/drone-categories/?search=Q"
    ordering_fields = (
        'name',
    )


class DroneCategoryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = DroneCategory.objects.all()
    serializer_class = DroneCategorySerializer
    name = 'dronecategory-detail'


# The throttling policies for the DroneList, DroneDetail
class DroneList(generics.ListCreateAPIView):
    queryset = Drone.objects.all()
    serializer_class = DroneSerializer
    name = 'drone-list'

    throttle_scope = 'drones'
    throttle_classes = (ScopedRateThrottle,)

    filter_fields = (
        'name',
        'drone_category',
        'manufacturing_date',
        'has_it_competed',
    )
    search_fields = (
        '^name',                      # http ":8000/drones/?search=G"
        # for Foreign Key add __name:
        'drone_category__name',       # http ":8000/drones/?search=Octocopter&ordering=-name"
    )
    ordering_fields = (
        'name',
        'manufacturing_date',
    )
    permission_classes = (permissions.IsAuthenticatedOrReadOnly, IsCurrentUserOwnerOrReadOnly)

    def perform_create(self, serializer):
        # Whenever a new Drone is created, it will save the User associated to the request as its owner
        serializer.save(owner=self.request.user)


class DroneDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Drone.objects.all()
    serializer_class = DroneSerializer
    name = 'drone-detail'

    throttle_scope = 'drones'
    throttle_classes = (ScopedRateThrottle,)


    permission_classes = (permissions.IsAuthenticatedOrReadOnly, IsCurrentUserOwnerOrReadOnly)


class PilotList(generics.ListCreateAPIView):
    queryset = Pilot.objects.all()
    serializer_class = PilotSerializer
    name = 'pilot-list'

    filter_fields = (
        'name',
        'gender',
        'races_count',
    )
    search_fields = (
        '^name',
    )
    ordering_fields = (
        'name',
        'races_count'
    )


class PilotDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Pilot.objects.all()
    serializer_class = PilotSerializer
    name = 'pilot-detail'


class CompetitionFilter(filters.FilterSet):
    from_achievement_date = DateTimeFilter(field_name='distance_achievement_date', lookup_expr='gte')
    to_achievement_date = DateTimeFilter(field_name='distance_achievement_date', lookup_expr='lte')
    min_distance_in_feet = NumberFilter(field_name='distance_in_feet', lookup_expr='gte')
    max_distance_in_feet = NumberFilter(field_name='distance_in_feet', lookup_expr='lte')
    drone_name = AllValuesFilter(field_name='drone__name')
    pilot_name = AllValuesFilter(field_name='pilot__name')
    # Example:
    # http ":8000/competitions/?pilot_name=Penelope+Pitstop&drone_name=WonderDrone"

    class Meta:
        model = Competition
        fields = ('distance_in_feet',
                  'from_achievement_date',
                  'to_achievement_date',
                  'min_distance_in_feet',
                  'max_distance_in_feet',
                  # drone__name will be accessed as drone_name
                  'drone_name',
                  # pilot__name will be accessed as pilot_name
                  'pilot_name',
                )


class CompetitionList(generics.ListCreateAPIView):
    queryset = Competition.objects.all()
    serializer_class = PilotCompetitionSerializer
    name = 'competition-list'

    filterset_class = CompetitionFilter
    ordering_fields = (
        'distance_in_feet',
        'distance_achievement_date',
    )

    # Example:
    # http ":8000/competitions/?min_distance_in_feet=790&max_distance_in_feet=900"
    # http GET ":8000/competitions/?from_achievement_date=2017-10-18&to_achievement_date=2017-10-22&min_distance_in_feet=700&max_distance_in_feet=900"
    # http GET ":8000/competitions/?from_achievement_date=2017-10-18&to_achievement_date=2017-10-22&min_distance_in_feet=2000"


class CompetitionDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Competition.objects.all()
    serializer_class = PilotCompetitionSerializer
    name = 'competition-detail'


class ApiRoot(generics.GenericAPIView):
    name = 'API Root'

    def get(self, request, *args, **kwargs):
        return Response(
            {
                'drone-categories': reverse(DroneCategoryList.name, request=request),
                'drones': reverse(DroneList.name, request=request),
                'pilots': reverse(PilotList.name, request=request),
                'competitions': reverse(CompetitionList.name, request=request),
            }
        )


# Create a new drone:
# http -a "admin":"123"  POST :8000/drones/ name="Python Drone" drone_category="Quadcopter" manufacturing_date="2017-08-16T02:02:00.716312Z" has_it_competed=false

# To check the throttling policy:
# Unauthenticated user:
# for i in {1..4}; do http :8000/competitions/; done;                           -> 429 Error Too Many Requests
# Authenticated user:
#  for i in {1..4}; do http -a "admin":"123" :8000/competitions/; done;         -> 200 OK
# Both the DroneList and the DroneDetail class accumulate in the same scope: 20 + 1 -> 429 Error
