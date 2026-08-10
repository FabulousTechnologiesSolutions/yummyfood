from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAuthenticatedAndActive
from apps.restaurants.serializers import (
    AvailabilitySerializer,
    CategoryCreateSerializer,
    CategoryReorderSerializer,
    CategoryUpdateSerializer,
    DealCreateSerializer,
    DealUpdateSerializer,
    MenuItemCreateSerializer,
    MenuItemUpdateSerializer,
    MoveMenuItemSerializer,
)
from apps.restaurants.services import (
    CategoryService,
    DealService,
    MenuItemService,
    RestaurantService,
    serialize_category,
    serialize_deal,
    serialize_menu_item,
)
from core.exceptions import AppAPIException
from core.permissions import IsRestaurantMode, IsRestaurantOwner


class RestaurantOwnerMixin:
    permission_classes = [IsAuthenticatedAndActive, IsRestaurantOwner, IsRestaurantMode]

    def get_restaurant(self, request):
        restaurant = getattr(request.user, 'restaurant', None)
        if restaurant is None:
            raise AppAPIException(
                code='RESTAURANT_REQUIRED',
                message='Restaurant profile required.',
                status_code=403,
            )
        return restaurant


# ---- Categories ----

class CategoryListCreateView(RestaurantOwnerMixin, APIView):
    def get(self, request):
        items = CategoryService().list()
        return Response([serialize_category(c) for c in items])

    @extend_schema(request=CategoryCreateSerializer)
    def post(self, request):
        serializer = CategoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = CategoryService().create(data=serializer.validated_data)
        return Response(serialize_category(category), status=status.HTTP_201_CREATED)


class CategoryDetailView(RestaurantOwnerMixin, APIView):
    @extend_schema(request=CategoryUpdateSerializer)
    def patch(self, request, category_id):
        serializer = CategoryUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        category = CategoryService().update(
            category_id=category_id,
            data=serializer.validated_data,
        )
        return Response(serialize_category(category))

    def delete(self, request, category_id):
        CategoryService().delete(category_id=category_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryReorderView(RestaurantOwnerMixin, APIView):
    @extend_schema(request=CategoryReorderSerializer)
    def post(self, request):
        serializer = CategoryReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = CategoryService().reorder(
            ordered_ids=serializer.validated_data['ordered_ids'],
        )
        return Response([serialize_category(c) for c in items])


# ---- Menu items ----

class MenuItemListCreateView(RestaurantOwnerMixin, APIView):
    def get(self, request):
        restaurant = self.get_restaurant(request)
        items = MenuItemService().list(restaurant=restaurant)
        return Response([serialize_menu_item(i) for i in items])

    @extend_schema(request=MenuItemCreateSerializer)
    def post(self, request):
        serializer = MenuItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = MenuItemService().create(
            restaurant=self.get_restaurant(request),
            data=serializer.validated_data,
        )
        return Response(serialize_menu_item(item), status=status.HTTP_201_CREATED)


class MenuItemDetailView(RestaurantOwnerMixin, APIView):
    def get(self, request, item_id):
        item = MenuItemService().get(
            restaurant=self.get_restaurant(request),
            item_id=item_id,
        )
        return Response(serialize_menu_item(item))

    @extend_schema(request=MenuItemUpdateSerializer)
    def patch(self, request, item_id):
        serializer = MenuItemUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        item = MenuItemService().update(
            restaurant=self.get_restaurant(request),
            item_id=item_id,
            data=serializer.validated_data,
        )
        return Response(serialize_menu_item(item))

    def delete(self, request, item_id):
        MenuItemService().delete(
            restaurant=self.get_restaurant(request),
            item_id=item_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MenuItemDuplicateView(RestaurantOwnerMixin, APIView):
    def post(self, request, item_id):
        item = MenuItemService().duplicate(
            restaurant=self.get_restaurant(request),
            item_id=item_id,
        )
        return Response(serialize_menu_item(item), status=status.HTTP_201_CREATED)


class MenuItemMoveView(RestaurantOwnerMixin, APIView):
    @extend_schema(request=MoveMenuItemSerializer)
    def post(self, request, item_id):
        serializer = MoveMenuItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = MenuItemService().move(
            restaurant=self.get_restaurant(request),
            item_id=item_id,
            category_id=serializer.validated_data['category_id'],
        )
        return Response(serialize_menu_item(item))


class MenuItemHideView(RestaurantOwnerMixin, APIView):
    def post(self, request, item_id):
        item = MenuItemService().hide(
            restaurant=self.get_restaurant(request),
            item_id=item_id,
        )
        return Response(serialize_menu_item(item))


class MenuItemAvailabilityView(RestaurantOwnerMixin, APIView):
    @extend_schema(request=AvailabilitySerializer)
    def patch(self, request, item_id):
        serializer = AvailabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = MenuItemService().set_availability(
            restaurant=self.get_restaurant(request),
            item_id=item_id,
            is_available=serializer.validated_data['is_available'],
        )
        return Response(serialize_menu_item(item))


# ---- Deals ----

class DealListCreateView(RestaurantOwnerMixin, APIView):
    def get(self, request):
        segment = request.query_params.get('segment', 'active')
        deals = DealService().list(
            restaurant=self.get_restaurant(request),
            segment=segment,
        )
        return Response([serialize_deal(d) for d in deals])

    @extend_schema(request=DealCreateSerializer)
    def post(self, request):
        serializer = DealCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        deal = DealService().create(
            restaurant=self.get_restaurant(request),
            data=serializer.validated_data,
        )
        return Response(serialize_deal(deal), status=status.HTTP_201_CREATED)


class DealDetailView(RestaurantOwnerMixin, APIView):
    def get(self, request, deal_id):
        deal = DealService().get(
            restaurant=self.get_restaurant(request),
            deal_id=deal_id,
        )
        return Response(serialize_deal(deal))

    @extend_schema(request=DealUpdateSerializer)
    def patch(self, request, deal_id):
        serializer = DealUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        deal = DealService().update(
            restaurant=self.get_restaurant(request),
            deal_id=deal_id,
            data=serializer.validated_data,
        )
        return Response(serialize_deal(deal))

    def delete(self, request, deal_id):
        DealService().delete(
            restaurant=self.get_restaurant(request),
            deal_id=deal_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class DealPreviewView(RestaurantOwnerMixin, APIView):
    def get(self, request, deal_id):
        payload = DealService().preview(
            restaurant=self.get_restaurant(request),
            deal_id=deal_id,
        )
        return Response(payload)


# ---- Public ----

class PublicRestaurantDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, restaurant_id):
        payload = RestaurantService().public_profile(restaurant_id, request=request)
        return Response(payload)


class PublicMenuItemDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, item_id):
        item = MenuItemService().get_public(item_id)
        return Response(serialize_menu_item(item))


class PublicDealDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, deal_id):
        deal = DealService().get_public(deal_id)
        return Response(serialize_deal(deal))
