from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from .models import (
    Card,
    Station,
    Reclamation,
    Attachment,
    ReclamationUpdate,
    Transaction,
)

User = get_user_model()


# UTILISATEURS

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib import messages
import logging
from .models import User

logger = logging.getLogger(__name__)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_specialist", "is_staff", 
                   "is_active", "date_joined", "assigned_station")
    search_fields = ("username", "email")
    list_filter = ("role", "is_staff", "is_active", "teams")
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = UserAdmin.fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('role', 'phone', 'teams', 'assigned_station')
        }),
    )

    def save_model(self, request, obj, form, change):
        """Surcharge pour l'admin"""
        super().save_model(request, obj, form, change)
        
        if change and 'role' in form.changed_data:
            from .utils import assign_user_to_team
            assign_user_to_team(obj)



# CARTES

@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("card_number", "card_type", "user", "balance", "is_active")
    list_filter = ("card_type", "is_active")
    search_fields = ("card_number", "user__username")
    ordering = ("card_number",)



# STATIONS

@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "code", "manager")
    search_fields = ("name", "city", "code")
    ordering = ("city", "name")
    raw_id_fields = ("manager",)



# RÉCLAMATIONS

@admin.register(Reclamation)
class ReclamationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "card_type",
        "problem_type",
        "status_colored",
        "priority",
        "get_assigned_team",
        "get_assigned_specialist",
        "station",
        "user",
        "created_at",
    )
    list_filter = (
        "status",
        "priority",
        "assigned_team",
        "station",
        "problem_type",
        "card_type",
    )
    search_fields = (
        "card_type",
        "card_number_manual",
        "problem_type",
        "description",
        "user__username",
        "assigned_specialist__username",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "station_coords")
    raw_id_fields = ("user", "station", "assigned_specialist", "assigned_agent")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request.user, 'is_specialist') and request.user.is_specialist:
            return qs.filter(assigned_specialist=request.user)
        return qs

    def status_colored(self, obj):
        colors = {
            "OPEN": "orange",
            "IN_PROGRESS": "blue",
            "RESOLVED": "green",
            "REJECTED": "red",
        }
        color = colors.get(obj.status, "black")
        return format_html(f"<b style='color:{color}'>{obj.get_status_display()}</b>")
    status_colored.short_description = "Statut"

    def get_assigned_team(self, obj):
        return obj.get_assigned_team_display() if obj.assigned_team else "-"
    get_assigned_team.short_description = "Équipe"

    def get_assigned_specialist(self, obj):
        return obj.assigned_specialist.username if obj.assigned_specialist else "-"
    get_assigned_specialist.short_description = "Spécialiste"

    actions = ["mark_as_resolved", "assign_to_team"]

    def mark_as_resolved(self, request, queryset):
        count = queryset.update(status="RESOLVED")
        self.message_user(request, f"{count} réclamation(s) marquée(s) comme résolue.")
    mark_as_resolved.short_description = "✅ Marquer comme résolue"

    def assign_to_team(self, request, queryset):
        from .utils import assign_reclamation
        count = 0
        for reclamation in queryset:
            assign_reclamation(reclamation)
            count += 1
        self.message_user(request, f"{count} réclamation(s) réaffectée(s) à une équipe.")
    assign_to_team.short_description = "🔄 Réaffecter à une équipe"

# MISES a JOUR DES RÉCLAMATIONS

@admin.register(ReclamationUpdate)
class ReclamationUpdateAdmin(admin.ModelAdmin):
    list_display = ("reclamation", "author", "new_status", "created_at", "is_internal_note")
    list_filter = ("new_status", "is_internal_note")
    search_fields = ("reclamation__id", "author__username")
    ordering = ("-created_at",)
    raw_id_fields = ("reclamation", "author")


# PIÈCES JOINTES


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("reclamation", "file_type", "uploaded_at", "description_short")
    ordering = ("-uploaded_at",)
    list_filter = ("file_type",)
    search_fields = ("reclamation__id", "description")
    raw_id_fields = ("reclamation",)

    def description_short(self, obj):
        return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description
    description_short.short_description = "Description"


# TRANSACTIONS

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "amount_formatted",
        "card",
        "station",
        "transaction_type",
        "date",
        "is_successful",
    )
    list_filter = ("station", "transaction_type", "is_successful")
    search_fields = ("reference", "card__card_number")
    ordering = ("-date",)
    raw_id_fields = ("card", "station")

    def amount_formatted(self, obj):
        return f"{obj.amount:.2f} DT"
    amount_formatted.short_description = "Montant"
