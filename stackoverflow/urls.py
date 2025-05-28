from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.StackUserViewSet)
router.register(r'questions', views.StackQuestionViewSet)
router.register(r'answers', views.StackAnswerViewSet)
router.register(r'comments', views.StackCommentViewSet)
router.register(r'tags', views.StackTagViewSet)
router.register(r'badges', views.StackBadgeViewSet)
router.register(r'collectives', views.StackCollectiveViewSet)
router.register(r'stackoverflow', views.StackOverflowViewSet, basename='stackoverflow')
# router.register(r'tag-synonyms', views.StackTagSynonymViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 