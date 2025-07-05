# school/utils/charts.py

i#mport matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import seaborn as sns
import pandas as pd
import numpy as np
from io import BytesIO
import base64
from django.db.models import Count, Avg, Q, Sum
from datetime import datetime, timedelta
from school.models import *
from profiles.models import Student, CustomUser


class ChartGenerator:
    """Générateur de graphiques pour les statistiques scolaires"""
    
    @staticmethod
    def get_chart_as_base64(fig):
        """Convertit un graphique matplotlib en base64 pour l'affichage HTML"""
        buffer = BytesIO()
        fig.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        graphic = base64.b64encode(image_png)
        graphic = graphic.decode('utf-8')
        return graphic
    
    @staticmethod
    def generate_students_by_class_chart(school):
        """Génère un graphique des élèves par classe"""
        plt.style.use('seaborn-v0_8')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Données des élèves par classe
        classes_data = Classe.objects.filter(school=school).annotate(
            student_count=Count('students_in_class')
        ).values('name', 'student_count')
        
        if classes_data:
            df = pd.DataFrame(classes_data)
            
            # Créer le graphique en barres
            bars = ax.bar(df['name'], df['student_count'], 
                         color='skyblue', edgecolor='navy', alpha=0.7)
            
            # Ajouter les valeurs sur les barres
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                       f'{int(height)}', ha='center', va='bottom', fontweight='bold')
            
            ax.set_title(f'Répartition des Élèves par Classe - {school.name}', 
                        fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Classes', fontsize=12)
            ax.set_ylabel('Nombre d\'Élèves', fontsize=12)
            plt.xticks(rotation=45, ha='right')
            plt.grid(axis='y', alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Aucune donnée disponible', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_title(f'Répartition des Élèves par Classe - {school.name}')
        
        plt.tight_layout()
        chart = ChartGenerator.get_chart_as_base64(fig)
        plt.close(fig)
        return chart
    
    @staticmethod
    def generate_grades_distribution_chart(school, academic_period):
        """Génère un graphique de distribution des notes"""
        plt.style.use('seaborn-v0_8')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Récupération des notes
        grades = Grade.objects.filter(
            enrollment__course__school=school,
            enrollment__academic_period=academic_period
        ).values_list('score', flat=True)
        
        if grades:
            grades_list = [float(g) for g in grades]
            
            # Histogramme des notes
            ax.hist(grades_list, bins=20, color='lightgreen', 
                   edgecolor='darkgreen', alpha=0.7)
            
            # Ajouter une ligne de moyenne
            mean_grade = np.mean(grades_list)
            ax.axvline(mean_grade, color='red', linestyle='--', linewidth=2,
                      label=f'Moyenne: {mean_grade:.2f}')
            
            ax.set_title(f'Distribution des Notes - {academic_period.name}', 
                        fontsize=16, fontweight='bold')
            ax.set_xlabel('Notes', fontsize=12)
            ax.set_ylabel('Fréquence', fontsize=12)
            ax.legend()
            plt.grid(axis='y', alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Aucune note disponible', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_title(f'Distribution des Notes - {academic_period.name}')
        
        plt.tight_layout()
        chart = ChartGenerator.get_chart_as_base64(fig)
        plt.close(fig)
        return chart
    
    @staticmethod
    def generate_attendance_rate_chart(school, academic_period):
        """Génère un graphique des taux de présence par classe"""
        plt.style.use('seaborn-v0_8')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        classes = Classe.objects.filter(school=school)
        attendance_data = []
        
        for classe in classes:
            students = Student.objects.filter(current_classe=classe)
            if students.exists():
                total_attendances = Attendance.objects.filter(
                    enrollment__student__in=students,
                    enrollment__academic_period=academic_period
                ).count()
                
                present_attendances = Attendance.objects.filter(
                    enrollment__student__in=students,
                    enrollment__academic_period=academic_period,
                    is_present=True
                ).count()
                
                rate = (present_attendances / total_attendances * 100) if total_attendances > 0 else 0
                attendance_data.append({
                    'classe': classe.name,
                    'rate': rate
                })
        
        if attendance_data:
            df = pd.DataFrame(attendance_data)
            
            # Graphique en barres horizontales
            bars = ax.barh(df['classe'], df['rate'], 
                          color='orange', edgecolor='darkorange', alpha=0.7)
            
            # Ajouter les pourcentages
            for i, bar in enumerate(bars):
                width = bar.get_width()
                ax.text(width + 1, bar.get_y() + bar.get_height()/2,
                       f'{width:.1f}%', ha='left', va='center', fontweight='bold')
            
            ax.set_title(f'Taux de Présence par Classe - {academic_period.name}', 
                        fontsize=16, fontweight='bold')
            ax.set_xlabel('Taux de Présence (%)', fontsize=12)
            ax.set_ylabel('Classes', fontsize=12)
            ax.set_xlim(0, 100)
            plt.grid(axis='x', alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Aucune donnée de présence disponible', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_title(f'Taux de Présence par Classe - {academic_period.name}')
        
        plt.tight_layout()
        chart = ChartGenerator.get_chart_as_base64(fig)
        plt.close(fig)
        return chart
    
    @staticmethod
    def generate_payment_status_chart(school, academic_period):
        """Génère un graphique des statuts de paiement"""
        plt.style.use('seaborn-v0_8')
        fig, ax = plt.subplots(figsize=(8, 8))
        
        payment_data = Payment.objects.filter(
            school=school,
            academic_period=academic_period
        ).values('payment_status').annotate(count=Count('payment_status'))
        
        if payment_data:
            labels = []
            sizes = []
            colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
            
            for item in payment_data:
                # Convertir le code en label lisible
                status_dict = dict(Payment.payment_status_choices)
                labels.append(status_dict.get(item['payment_status'], item['payment_status']))
                sizes.append(item['count'])
            
            # Graphique en secteurs
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                            colors=colors, startangle=90,
                                            explode=[0.05] * len(sizes))
            
            # Améliorer l'apparence
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            ax.set_title(f'Statuts des Paiements - {academic_period.name}', 
                        fontsize=16, fontweight='bold', pad=20)
        else:
            ax.text(0.5, 0.5, 'Aucune donnée de paiement disponible', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_title(f'Statuts des Paiements - {academic_period.name}')
        
        plt.tight_layout()
        chart = ChartGenerator.get_chart_as_base64(fig)
        plt.close(fig)
        return chart
    
    @staticmethod
    def generate_monthly_payments_chart(school, year=None):
        """Génère un graphique des paiements par mois"""
        plt.style.use('seaborn-v0_8')
        fig, ax = plt.subplots(figsize=(12, 6))
        
        if not year:
            year = datetime.now().year
        
        # Données des paiements par mois
        monthly_data = []
        months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
                 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
        
        for month in range(1, 13):
            total = Payment.objects.filter(
                school=school,
                payment_date__year=year,
                payment_date__month=month
            ).aggregate(total=Sum('amount_paid'))['total'] or 0
            monthly_data.append(float(total))
        
        if any(monthly_data):
            # Graphique en barres
            bars = ax.bar(months, monthly_data, 
                         color='mediumpurple', edgecolor='indigo', alpha=0.7)
            
            # Ajouter les valeurs sur les barres
            for bar, value in zip(bars, monthly_data):
                if value > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + max(monthly_data) * 0.01,
                           f'{value:.0f}€', ha='center', va='bottom', fontweight='bold')
            
            ax.set_title(f'Évolution des Paiements par Mois - {year}', 
                        fontsize=16, fontweight='bold')
            ax.set_xlabel('Mois', fontsize=12)
            ax.set_ylabel('Montant Total (€)', fontsize=12)
            plt.xticks(rotation=45)
            plt.grid(axis='y', alpha=0.3)
        else:
            ax.text(0.5, 0.5, f'Aucun paiement en {year}', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_title(f'Évolution des Paiements par Mois - {year}')
        
        plt.tight_layout()
        chart = ChartGenerator.get_chart_as_base64(fig)
        plt.close(fig)
        return chart
    
    @staticmethod
    def generate_teacher_performance_chart(school, academic_period):
        """Génère un graphique de performance des enseignants (basé sur les moyennes de leurs élèves)"""
        plt.style.use('seaborn-v0_8')
        fig, ax = plt.subplots(figsize=(12, 6))
        
        teachers = CustomUser.objects.filter(
            user_type='TEACHER', 
            school=school
        )
        
        teacher_data = []
        
        for teacher in teachers:
            # Récupérer les classes enseignées par ce professeur
            taught_classes = Classe.objects.filter(teachers=teacher)
            
            if taught_classes.exists():
                all_grades = []
                for classe in taught_classes:
                    students = Student.objects.filter(current_classe=classe)
                    for student in students:
                        grades = Grade.objects.filter(
                            enrollment__student=student,
                            enrollment__academic_period=academic_period
                        )
                        for grade in grades:
                            # Normaliser sur 20
                            normalized_score = (float(grade.score) / float(grade.evaluation.max_score)) * 20
                            all_grades.append(normalized_score)
                
                if all_grades:
                    avg_grade = np.mean(all_grades)
                    teacher_data.append({
                        'teacher': f"{teacher.first_name} {teacher.last_name}",
                        'average': avg_grade,
                        'students_count': len(all_grades)
                    })
        
        if teacher_data:
            df = pd.DataFrame(teacher_data)
            df = df.sort_values('average', ascending=True)
            
            # Graphique en barres horizontales
            bars = ax.barh(df['teacher'], df['average'], 
                          color='lightcoral', edgecolor='darkred', alpha=0.7)
            
            # Ajouter les moyennes
            for i, bar in enumerate(bars):
                width = bar.get_width()
                ax.text(width + 0.1, bar.get_y() + bar.get_height()/2,
                       f'{width:.1f}/20', ha='left', va='center', fontweight='bold')
            
            ax.set_title(f'Performance des Enseignants - {academic_period.name}', 
                        fontsize=16, fontweight='bold')
            ax.set_xlabel('Moyenne des Notes des Élèves (/20)', fontsize=12)
            ax.set_ylabel('Enseignants', fontsize=12)
            ax.set_xlim(0, 20)
            plt.grid(axis='x', alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Aucune donnée disponible', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_title(f'Performance des Enseignants - {academic_period.name}')
        
        plt.tight_layout()
        chart = ChartGenerator.get_chart_as_base64(fig)
        plt.close(fig)
        return chart
    
    @staticmethod
    def generate_class_comparison_chart(school, academic_period):
        """Génère un graphique de comparaison des moyennes par classe"""
        plt.style.use('seaborn-v0_8')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        classes = Classe.objects.filter(school=school)
        class_data = []
        
        for classe in classes:
            students = Student.objects.filter(current_classe=classe)
            all_grades = []
            
            for student in students:
                grades = Grade.objects.filter(
                    enrollment__student=student,
                    enrollment__academic_period=academic_period
                )
                for grade in grades:
                    normalized_score = (float(grade.score) / float(grade.evaluation.max_score)) * 20
                    all_grades.append(normalized_score)
            
            if all_grades:
                class_data.append({
                    'classe': classe.name,
                    'average': np.mean(all_grades),
                    'count': len(all_grades)
                })
        
        if class_data:
            df = pd.DataFrame(class_data)
            
            # Graphique en barres avec couleurs graduées
            colors = plt.cm.viridis(np.linspace(0, 1, len(df)))
            bars = ax.bar(df['classe'], df['average'], 
                         color=colors, edgecolor='black', alpha=0.8)
            
            # Ajouter les moyennes sur les barres
            for bar, avg in zip(bars, df['average']):
                ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.1,
                       f'{avg:.1f}', ha='center', va='bottom', fontweight='bold')
            
            # Ligne de moyenne générale
            overall_avg = df['average'].mean()
            ax.axhline(overall_avg, color='red', linestyle='--', linewidth=2,
                      label=f'Moyenne générale: {overall_avg:.1f}')
            
            ax.set_title(f'Comparaison des Moyennes par Classe - {academic_period.name}', 
                        fontsize=16, fontweight='bold')
            ax.set_xlabel('Classes', fontsize=12)
            ax.set_ylabel('Moyenne (/20)', fontsize=12)
            ax.set_ylim(0, 20)
            plt.xticks(rotation=45, ha='right')
            plt.legend()
            plt.grid(axis='y', alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Aucune donnée disponible', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_title(f'Comparaison des Moyennes par Classe - {academic_period.name}')
        
        plt.tight_layout()
        chart = ChartGenerator.get_chart_as_base64(fig)
        plt.close(fig)
        return chart