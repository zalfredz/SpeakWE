from django.urls import path

from . import views

urlpatterns = [
    path("sessions", views.create_session),
    path("sessions/<uuid:session_id>", views.session_detail),
    path("sessions/<uuid:session_id>/state", views.session_state),
    path("sessions/<uuid:session_id>/turns/<int:index>/begin", views.begin_turn),
    path("sessions/<uuid:session_id>/turns/<int:index>/answer", views.answer_turn),
    path("sessions/<uuid:session_id>/complete", views.complete_session),
    path("sessions/<uuid:session_id>/report", views.session_report),
    path("sessions/<uuid:session_id>/assess", views.reassess),
    path("sessions/<uuid:session_id>/turns/<int:index>/audio", views.turn_audio),
    path("checkins", views.checkins),
]
