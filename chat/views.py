from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Conversation, Message


@login_required
def conversations(request):
    """List all conversations for the current user."""
    if request.user.role == 'worker':
        convos = Conversation.objects.filter(worker=request.user)
    else:
        convos = Conversation.objects.filter(employer=request.user)

    convos = convos.select_related('job', 'worker', 'employer')
    return render(request, 'chat/conversations.html', {'conversations': convos})


@login_required
def chat(request, conversation_id):
    """View and send messages in a conversation."""
    conversation = get_object_or_404(Conversation, id=conversation_id)

    if request.user not in [conversation.worker, conversation.employer]:
        messages.error(request, 'Access denied.')
        return redirect('conversations')

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=content
            )
        return redirect('chat', conversation_id=conversation_id)

    chat_messages = conversation.messages.select_related('sender')
    other_user = conversation.employer if request.user == conversation.worker else conversation.worker

    return render(request, 'chat/chat.html', {
        'conversation': conversation,
        'chat_messages': chat_messages,
        'other_user': other_user,
    })
