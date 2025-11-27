from django.shortcuts import render
def landing(request):
    return render(request, "web/landing.html")

def mentors(request):
    return render(request, "web/mentors.html")
