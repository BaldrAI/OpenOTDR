using System.Collections.ObjectModel;
using Microsoft.EntityFrameworkCore;
using OpenOTDR.Models;
using OpenOTDR.Services;

namespace OpenOTDR.Pages;


public partial class ProjectsPage : ContentPage
{
    public ObservableCollection<Project> projects;

    async void OnTapped(object sender, EventArgs eventArgs)
    {
        Grid context = (Grid)sender;
        Project project =(Project)context.BindingContext;
        ProjectsContext.TrackedProject = project;
        await Shell.Current.GoToAsync($"projectOverview");
    }

    async void OnDeleted(object sender, EventArgs eventArgs)
    {
        Grid context = (Grid)sender;
        Project project = (Project)context.BindingContext;
        string question = "Are you sure to want to Permanently Delete " + project.Name;
        bool answer = await DisplayAlert("Question?", question, "Yes", "No");
        if (answer)
        {
            projects.Remove(project);
            await Constants.ctx.SaveChangesAsync();
        }
    }

    async void OnNewEnter(object sender, EventArgs eventArgs)
    {
        Entry context = (Entry)sender;
        var project = new Project()
        {
            Name=context.Text,
            A=new (),
            B=new (), 
            Customer=new ()
            {
                BillingContact = new(), 
                TechnicalContact = new()
            },
            IsDefault = false
        };
        projects.Add(project);
        await Constants.ctx.SaveChangesAsync();
        ProjectsContext.TrackedProject = project;
        context.Text = "";
        await Shell.Current.GoToAsync($"projectOverview");
    }


    public ProjectsPage()
    {
        Constants.ctx.Projects.Load();
        Constants.ctx.Contacts.Load();
        Constants.ctx.Customers.Load();
        Constants.ctx.Locations.Load();
        Constants.ctx.Files.Load();
        projects = Constants.ctx.Projects.Local.ToObservableCollection();
        Routing.RegisterRoute("projectOverview", typeof(ProjectOverviewPage));
        Routing.RegisterRoute("projectTrace", typeof(ProjectTracePage));
        InitializeComponent();
        BindableLayout.SetItemsSource(FlexProjects, projects);
    }

}

public class ProjectDataTemplateSelector : DataTemplateSelector
{
    public DataTemplate NewRecord { get; set; }
    public DataTemplate ExistingRecord { get; set; }

    protected override DataTemplate OnSelectTemplate(object item, BindableObject container)
    {
        return ((Project)item).IsDefault ? NewRecord : ExistingRecord;
    }
}