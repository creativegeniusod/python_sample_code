from django.conf.urls import url
from chat import views
from django.views.decorators.csrf import csrf_exempt


urlpatterns = [
    url(r'^getChatBox', views.getChatBox, name='getChatBox'),
    url(r'^guestgetChatBoxG', views.guestgetChatBoxG, name='guestgetChatBoxG'),
    url(r'^saveChatMessage', views.saveChatMessage, name='saveChatMessage'),
    url(r'^guestsaveChatMessageG', views.guestsaveChatMessageG, name='guestsaveChatMessageG'),
    url(r'^uploadAttachments', csrf_exempt(views.uploadAttachments), name='uploadAttachments'),
    url(r'^getNewMessagesLive', views.getNewMessagesLive, name='getNewMessagesLive'),
    url(r'^guestNewMessagesLiveG', views.guestNewMessagesLiveG, name='guestNewMessagesLiveG'),
    url(r'^sendInviteEmail', views.sendInviteEmail, name='sendInviteEmail'),
    url(r'^getNewMessage', views.getNewMessage, name='getNewMessage')
]