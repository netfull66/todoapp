from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import UnloggedUserTask, LoggedUserTask, ProUserTask, Project, TaskFeedback, Invitation,CustomUser,SubscriptionOrder
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm,ProjectForm
from datetime import datetime, timedelta
import uuid
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.utils.timezone import now
from django.contrib import messages
import requests
from django.http import HttpResponseRedirect


# Function to handle user registration
def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password']
        password2 = request.POST['confirm_password']
        
        if password1 != password2:
            messages.error(request, "Passwords do not match!")
            return redirect('register')
        
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return redirect('register')
        
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered!")
            return redirect('register')
        
        user = CustomUser.objects.create_user(username=username, email=email, password=password1)
        user.save()

    return render(request, 'register.html')

    return render(request, 'register.html', {'form': form})
# Function to handle user login
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})
# Function to create a task for unlogged users
def create_task(request):
    if request.method == 'POST':
        task_name = request.POST.get('task_name')

        if request.user.is_authenticated:
            # For logged and pro users
            if request.user.subscription_type == 'pro':
                # Pro user task creation
                project_id = request.POST.get('project_id')
                project = get_object_or_404(Project, id=project_id) if project_id else None
                file = request.FILES.get('file')
                task = ProUserTask.objects.create(user=request.user, task_name=task_name, project=project)
                return redirect('dashboard')
            else:
                # Logged user task creation
                task = LoggedUserTask.objects.create(user=request.user, task_name=task_name)
                return redirect('dashboard')
        else:
            # For unlogged user task creation
            ip_address = get_client_ip(request)
            task = UnloggedUserTask.objects.create(ip_address=ip_address, task_name=task_name)
            return redirect('dashboard')

    # For GET request, provide the project list for pro users
    if request.user.is_authenticated and request.user.subscription_type == 'pro':
        projects = Project.objects.filter(created_by=request.user)
        return render(request, 'create_task.html', {'projects': projects})

    return render(request, 'create_task.html')

# Function to create a project
@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user  # Set the creator as the logged-in user (team leader)

            # Set the start_date if it is not already provided in the form
            if not project.start_date:
                project.start_date = timezone.now()  # Set the current date and time as the start date

            project.save()
            return redirect('project_detail', project_id=project.id)  # Redirect to the project detail page
    else:
        form = ProjectForm()

    return render(request, 'create_project.html', {'form': form})

# Function to submit feedback for a task
@login_required
def submit_feedback(request, task_id):
    task = get_object_or_404(ProUserTask, id=task_id, user=request.user)
    if request.method == 'POST':
        feedback_text = request.POST.get('feedback')
        feedback = TaskFeedback.objects.create(task=task, feedback=feedback_text)
        return render(request, 'feedback_submitted.html', {'feedback': feedback})
    return render(request, 'submit_feedback.html', {'task': task})

# Function to view invitations
@login_required
def view_invitations(request):
    invitations = Invitation.objects.filter(team_leader=request.user)
    return render(request, 'invitations.html', {'invitations': invitations})

# Function to send an invitation
@login_required
def send_invitation(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        project_id = request.POST.get('project_id')
        project = get_object_or_404(Project, id=project_id, created_by=request.user)

        invitation = Invitation.objects.create(
            team_leader=request.user,
            name=name,
            email=email,
            token=generate_unique_token(),
            project=project
        )
        return render(request, 'invitation_sent.html', {'invitation': invitation})

    projects = Project.objects.filter(created_by=request.user)
    return render(request, 'send_invitation.html', {'projects': projects})

def dashboard_view(request):
    user = request.user
    context = {}

    if user.is_authenticated:
        if user.subscription_type == 'pro':
            tasks = ProUserTask.objects.filter(user=user).order_by('-created_at')
        else:
            user_tasks = LoggedUserTask.objects.filter(user=user).order_by('-created_at')
            assigned_tasks = ProUserTask.objects.filter(assigned_to=user).order_by('-created_at')
            # Combine and sort the querysets
            tasks = sorted(
                list(user_tasks) + list(assigned_tasks),
                key=lambda t: t.created_at,
                reverse=True
            )

        # Calculate completed tasks count
        completed_task_count = sum(1 for task in tasks if task.is_done)  # Manual filtering for lists

        # Slice the tasks list to get the first 5
        tasks = tasks[:5]

        context['tasks'] = tasks
        context['task_count'] = len(tasks)  # Add the task count here
        context['completed_task_count'] = completed_task_count  # Add completed task count here
        context['is_pro_user'] = user.subscription_type == 'pro'
        context['user'] = user

        return render(request, 'index.html', context)

    else:
        ip_address = get_client_ip(request)
        tasks = UnloggedUserTask.objects.filter(ip_address=ip_address).order_by('-created_at')

        # Calculate completed tasks count
        completed_task_count = tasks.filter(is_done=True).count()

        # Slice the tasks list to get the first 5
        tasks = tasks[:5]

        context['tasks'] = tasks
        context['task_count'] = len(tasks)  # Add the task count here
        context['completed_task_count'] = completed_task_count  # Add completed task count here

        return render(request, 'index.html', context)

@login_required
def user_projects_view(request):
    """
    Fetch projects related to the authenticated user and render the 'tab-panel.html' template.
    """
    user = request.user

    # Fetch projects created by the user and projects where the user is a member
    created_projects = Project.objects.filter(created_by=user)
    member_projects = Project.objects.filter(members=user)

    # Combine QuerySets into a Python list and remove duplicates
    user_projects = list(created_projects) + list(member_projects)
    unique_projects = {project.id: project for project in user_projects}.values()  # Deduplicate by project ID

    # Context data for the template
    context = {
        'projects': unique_projects
    }

    return render(request, 'projects.html', context)

def user_tasks_view(request):
    """
    Fetch tasks for a user based on their authentication and subscription status
    and render the 'tasks.html' template.
    """
    user = request.user
    context = {}

    if user.is_authenticated:
        if user.subscription_type == 'pro':
            # Fetch Pro user tasks
            pro_tasks = ProUserTask.objects.filter(user=user)
            context['tasks'] = pro_tasks
        else:
            # Fetch tasks directly created by the free user
            user_tasks = LoggedUserTask.objects.filter(user=user)

            # Fetch tasks assigned to the free user by Pro users
            assigned_tasks = ProUserTask.objects.filter(assigned_to=user)

            # Combine the tasks into a single list
            context['tasks'] = list(user_tasks) + list(assigned_tasks)

        # Add user subscription type to context
        context['is_pro_user'] = user.subscription_type == 'pro'
    else:
        # Handle unlogged users
        ip_address = get_client_ip(request)  # Fetch the IP address of the user
        unlogged_tasks = UnloggedUserTask.objects.filter(ip_address=ip_address)
        context['tasks'] = unlogged_tasks
        context['is_pro_user'] = False  # Not a logged-in user

    return render(request, 'tasks.html', context)



def update_task_status(request, task_id):
    if request.method == "POST":
        task = None
        if request.user.is_authenticated:
            # For logged-in users
            if request.user.subscription_type == 'pro':
                task = ProUserTask.objects.get(id=task_id, user=request.user)
            else:
                task = LoggedUserTask.objects.get(id=task_id, user=request.user)
        else:
            # For unlogged users (using IP address to identify)
            task = UnloggedUserTask.objects.get(id=task_id, ip_address=get_client_ip(request))

        # Toggle the task's `is_done` field
        task.is_done = not task.is_done
        task.save()

        return JsonResponse({'status': 'success', 'is_done': task.is_done})

    return JsonResponse({'status': 'failed'})


# Utility function to generate a unique token for invitations
def generate_unique_token():
    import uuid
    return str(uuid.uuid4())

# Function to get client IP address
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def trial_middleware(get_response):
    def middleware(request):
        if request.user.is_authenticated:
            user = request.user
            if user.subscription_type == 'free':
                if user.trial_start_date:
                    trial_end_date = user.trial_start_date + timedelta(weeks=2)
                    if datetime.now().date() > trial_end_date:
                        user.subscription_type = 'free'
                        user.role = 'expired'
                        user.save()
                        return redirect('trial_expired')
            elif user.subscription_type == 'pro':
                if user.pro_subscription_date and datetime.now().date() - user.pro_subscription_date > timedelta(weeks=4):
                    return redirect('pro_payment_required')
        return get_response(request)
    return middleware

@login_required
def subscribe_pro(request):
    user = request.user
    if request.method == 'POST':
        if user.subscription_type == 'free':
            if not user.pro_subscription_date or (now().date() - user.pro_subscription_date).days > 30:
                # Start a free Pro trial
                user.subscription_type = 'pro'
                user.role = 'team_leader'
                user.pro_subscription_date = now().date()
                user.save()
                messages.success(request, "Enjoy your free Pro trial!")
                return redirect('dashboard')
            else:
                messages.error(request, "You have already used your free trial. Please pay to subscribe.")
        elif user.subscription_type == 'pro':
            messages.info(request, "You are already subscribed to Pro.")
        return redirect('subscribe_pro')
    return render(request, 'subscribe_pro.html')



from django.core.mail import send_mail
from django.db import IntegrityError

@login_required
def invite_team_members(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    # Ensure only the project creator can invite members
    if request.user != project.created_by:
        return redirect('project_detail', project_id=project.id)

    if request.method == 'POST':
        email = request.POST.get("email")
        role = request.POST.get("role")  # Fetch the role from the POST data

        if email and role:
            try:
                # Check if the user already exists
                user, created = CustomUser.objects.get_or_create(email=email, defaults={"username": email.split("@")[0]})

                # Update the role for the user
                user.role = role
                user.save()

                # Create an invitation token
                token = uuid.uuid4()
                Invitation.objects.create(
                    email=email,
                    project=project,
                    team_leader=request.user,
                    token=token,
                )

                # Send invitation email
                send_invitation_email(request.user, email, token, request)

                return render(request, 'invitation_sent.html', {'email': email, 'project': project})

            except IntegrityError:
                # Handle the case where the email already has an invitation
                error_message = "This email has already been invited to the project."
                return render(request, 'add_team_members.html', {'project': project, 'error_message': error_message})

    return render(request, 'add_team_members.html', {'project': project})



def send_invitation_email(team_leader, email, token, request):
    # Use reverse to generate the URL for accepting the invitation
    invitation_link = request.build_absolute_uri(reverse('accept_invitation', kwargs={'token': token}))
    send_mail(
        subject="You're Invited to Join a Project!",
        message=f"Hi,\n\nYou've been invited by {team_leader.username} to join the project '{team_leader.username}'.\n\nClick the link below to accept the invitation:\n{invitation_link}\n\nThanks!",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )





@login_required
def accept_invitation(request, token):
    # Retrieve the invitation
    invitation = get_object_or_404(Invitation, token=token, accepted=False)

    # Add the logged-in user to the project's members
    project = invitation.project
    if request.user not in project.members.all():  # Avoid duplicate additions
        project.members.add(request.user)
    else:
        messages.warning(request, "You are already a member of this project.")

    # Check the role specified in the invitation
    if invitation.role == 'product_owner':
        # Assign "Product Owner" permissions (if applicable) or simply acknowledge
        messages.success(request, "You have joined the project as the Product Owner.")
    elif invitation.role == 'team_member':
        # Acknowledge the user as a team member
        messages.success(request, "You have joined the project as a Team Member.")

    # Mark the invitation as accepted
    invitation.accepted = True
    invitation.save()

    return render(request, 'invitation_accepted.html', {'project': project})


@login_required
def upload_task_file(request, task_id):
    task = get_object_or_404(ProUserTask, id=task_id)
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        task.uploaded_file = uploaded_file  # Assuming Task model has a file field
        task.save()
        return JsonResponse({'message': 'File uploaded successfully'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

from django.http import HttpResponse, Http404
import os


def download_file(request, task_id):
    # Get the task instance
    task = get_object_or_404(ProUserTask, id=task_id)
    
    # Check if the task has an uploaded file
    if not task.uploaded_file:
        raise Http404("No file found for this task.")

    # Construct the full file path
    file_path = os.path.join(settings.MEDIA_ROOT, task.uploaded_file.name)

    # Check if the file exists
    if not os.path.exists(file_path):
        raise Http404("File not found on the server.")

    # Serve the file as a response
    with open(file_path, 'rb') as file:
        response = HttpResponse(file.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        return response
    

import zipfile
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

def export_project_files(request, project_id):
    # Fetch the project and associated tasks
    project = get_object_or_404(Project, id=project_id)
    tasks = project.tasks.all()

    # Define a temporary zip file location
    zip_filename = f"{project.name}_files.zip"
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    zip_path = os.path.join(temp_dir, zip_filename)

    # Create the zip file
    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        for task in tasks:
            if task.uploaded_file and os.path.exists(task.uploaded_file.path):
                file_path = task.uploaded_file.path
                file_name = os.path.basename(file_path)
                # Add the file under a folder named after the task
                zip_file.write(file_path, arcname=f"{task.task_name}/{file_name}")

    # Serve the zip file as a downloadable response
    with open(zip_path, 'rb') as zip_file:
        response = HttpResponse(zip_file.read(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'

    # Clean up the temporary file
    os.remove(zip_path)

    return response



def view_project_tasks(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    # Ensure the user is the Product Owner of the project

    # Fetch all tasks related to this project
    tasks = project.tasks.all()

    return render(request, 'project_tasks.html', {
        'project': project,
        'tasks': tasks,
    })


@login_required
def reassign_task(request, task_id):
    # Fetch the task
    task = get_object_or_404(ProUserTask, id=task_id)

    # Ensure the user has permission to reassign the task
    if request.user != task.project.created_by and request.user.role != 'team_leader':
        return HttpResponseForbidden("You do not have permission to reassign this task.")
    
    if request.method == 'POST':
        # Get the new assignee's ID from the form
        new_assignee_id = request.POST.get('assigned_to')
        new_assignee = get_object_or_404(CustomUser, id=new_assignee_id)

        # Validate that the new assignee is a member of the project
        if new_assignee not in task.project.members.all():
            return HttpResponseForbidden("The selected user is not a member of this project.")

        # Reassign the task
        task.assigned_to = new_assignee
        task.save()

        # Redirect to the project detail page
        return redirect('project_detail', project_id=task.project.id)

    # Fetch the project members for the dropdown
    project_members = task.project.members.all()
    return render(request, 'reassign_task.html', {
        'task': task,
        'project_members': project_members,
    })


@login_required
def project_detail(request, project_id):
    # Fetch the project or return a 404 if it doesn't exist
    project = get_object_or_404(Project, id=project_id)

    # Ensure the user is either the project creator or a member of the project
    if request.user != project.created_by and request.user not in project.members.all():
        return HttpResponseForbidden("You do not have permission to view this project.")

    # Fetch tasks related to this project
    tasks = project.tasks.all()

    # Debugging output to confirm task query results
    print(f"Tasks for project {project_id}: {tasks}")

    # Render the project details page
    return render(request, 'project_detail.html', {
        'project': project,
        'tasks': tasks,
        'members': project.members.all()
    })

@login_required
def task_detail(request, task_id):
    task = get_object_or_404(ProUserTask, id=task_id)
    project = task.project

    # Ensure that the current user is the project leader
    if project.created_by != request.user:
        return HttpResponseForbidden("You are not authorized to manage tasks for this project.")

    # Handle feedback submission (approve or refuse)
    if request.method == "POST":
        action = request.POST.get('action')
        feedback_text = request.POST.get('feedback')

        if action == "approve":
            # Approve the task and mark it as done
            task_feedback, created = TaskFeedback.objects.get_or_create(task=task)
            task_feedback.approved = True
            task_feedback.feedback = ""
            task_feedback.save()

            # Mark the task as done
            task.mark_as_done()

        elif action == "refuse":
            # Refuse the task and save feedback
            task_feedback, created = TaskFeedback.objects.get_or_create(task=task)
            task_feedback.approved = False
            task_feedback.feedback = feedback_text
            task_feedback.save()

            # Task remains not done
            task.is_done = False
            task.save()

            # Delete the uploaded file if it exists
            if task.uploaded_file:
                task.uploaded_file.delete()

        return redirect('project_detail', project_id=project.id)

    # Get the current feedback for the task (if any)
    feedback = TaskFeedback.objects.filter(task=task).first()

    return render(request, 'task_detail.html', {
        'task': task,
        'feedback': feedback
    })

from .models import SubscriptionOrder
import uuid
import requests
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings
from .models import SubscriptionOrder

def pay(request):
    # Step 1: Set and Validate the Amount
    amount = 300  # Fixed amount in EGP
    if amount <= 0:
        messages.error(request, 'Invalid amount. Must be greater than zero.')
        return redirect('dashboard')

    # Step 2: Get Auth Token
    try:
        auth_response = requests.post(
            'https://accept.paymobsolutions.com/api/auth/tokens',
            json={'api_key': settings.PAYMOB_API_KEY}
        )
        auth_response.raise_for_status()
        auth_token = auth_response.json().get('token')
        if not auth_token:
            raise ValueError('No auth token received from Paymob.')
    except (requests.exceptions.RequestException, ValueError) as e:
        messages.error(request, f'Error obtaining auth token: {e}')
        return redirect('dashboard')

    # Step 3: Create Order
    try:
        unique_order_id = str(uuid.uuid4())
        order_response = requests.post(
            'https://accept.paymobsolutions.com/api/ecommerce/orders',
            json={
                'auth_token': auth_token,
                'delivery_needed': False,
                'amount_cents': amount * 100,  # Convert to cents
                'currency': 'EGP',
                'merchant_order_id': unique_order_id,
            }
        )
        order_response.raise_for_status()
        order_id = order_response.json().get('id')
        if not order_id:
            raise ValueError('No order ID received from Paymob.')
    except (requests.exceptions.RequestException, ValueError) as e:
        messages.error(request, f'Error creating order: {e}')
        return redirect('dashboard')

    # Step 4: Generate Payment Key
    try:
        billing_data = {
            'first_name': request.user.first_name or 'First',
            'last_name': request.user.last_name or 'Last',
            'street': '123 Main St',  # Replace with real data
            'building': '1',
            'floor': '1',
            'apartment': '1A',
            'city': 'Cairo',
            'state': 'Cairo',
            'country': 'EGY',  # ISO code
            'postal_code': '3753450',
            'email': request.user.email or 'user@example.com',
            'phone_number': '01145871860',
        }
        payment_key_response = requests.post(
            'https://accept.paymobsolutions.com/api/acceptance/payment_keys',
            json={
                'auth_token': auth_token,
                'amount_cents': amount * 100,
                'expiration': 3600,
                'order_id': order_id,
                'currency': 'EGP',
                'integration_id': settings.PAYMOB_INTEGRATION_ID,
                'billing_data': billing_data,
            }
        )
        payment_key_response.raise_for_status()
        payment_key = payment_key_response.json().get('token')
        if not payment_key:
            raise ValueError('No payment key received.')
    except (requests.exceptions.RequestException, ValueError) as e:
        messages.error(request, f'Error generating payment key: {e}')
        return redirect('dashboard')

    # Step 5: Create Subscription Order
    try:
        subscription_order = SubscriptionOrder.objects.create(
            user=request.user,
            payment_status='Pending',
            payment_key=payment_key,
            amount_cents=amount * 100,
        )
    except Exception as e:
        messages.error(request, f'Error creating subscription order: {e}')
        return redirect('dashboard')

    # Step 6: Redirect to Payment Page
    payment_url = f'https://accept.paymobsolutions.com/api/acceptance/iframes/{settings.PAYMOB_IFRAME_ID}?payment_token={payment_key}'
    return redirect(payment_url)


def payment_result(request):
    # Extract payment result data
    payment_data = request.POST
    payment_key = payment_data.get('payment_token')
    payment_status = payment_data.get('success', 'false') == 'true'

    try:
        # Fetch the related subscription order
        subscription_order = SubscriptionOrder.objects.filter(payment_key=payment_key).first()
        if not subscription_order:
            messages.error(request, 'Payment not found.')
            return redirect('dashboard')

        # Update payment and subscription details
        if payment_status:
            subscription_order.payment_status = 'Completed'
            subscription_order.save()

            # Update user's subscription
            user = subscription_order.user
            user.subscription_type = 'pro'
            user.pro_subscription_date = timezone.now().date()
            user.subscription_end_date = user.pro_subscription_date + timedelta(days=30)
            user.save()

            messages.success(request, 'Payment successful! Welcome to Pro membership.')
        else:
            subscription_order.payment_status = 'Failed'
            subscription_order.save()
            messages.error(request, 'Payment failed. Please try again.')
    except Exception as e:
        messages.error(request, f'Error processing payment result: {e}')

    return redirect('dashboard')

def payment_result(request):
    # Handle payment result callback
    payment_data = request.POST
    payment_key = payment_data.get('payment_token')
    payment_status = payment_data.get('success', False)

    try:
        subscription_order = SubscriptionOrder.objects.filter(payment_key=payment_key).first()
        if not subscription_order:
            messages.error(request, 'Payment not found.')
            return redirect('dashboard')

        if payment_status == 'true':  # Check if the payment was successful
            subscription_order.payment_status = 'Completed'
            subscription_order.save()

            # Update user subscription and set the 'Pro' subscription type
            user = subscription_order.user
            user.subscription_type = 'pro'
            user.pro_subscription_date = timezone.now().date()
            # Assuming 30 days for the subscription duration
            user.subscription_end_date = user.pro_subscription_date + timedelta(days=30)
            user.save()

            messages.success(request, 'Payment successful! You are now a Pro member.')
        else:
            subscription_order.payment_status = 'Failed'
            subscription_order.save()
            messages.error(request, 'Payment failed. Please try again.')
    except Exception as e:
        messages.error(request, f'An error occurred while updating payment status: {e}')

    return redirect('dashboard')
