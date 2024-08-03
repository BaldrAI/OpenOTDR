using fio = Microsoft.VisualBasic.FileIO;
using OpenOTDR.Models;
using OpenOTDR.Services;
using Microsoft.EntityFrameworkCore;

namespace OpenOTDR.Pages;

public partial class ProjectOverviewPage : ContentPage
{
    public Project TrackedProject => ProjectsContext.TrackedProject;

    private async void OnChangeName(object sender, EventArgs eventArgs)
    {
        var context = (Entry)sender;
        var existsReverting = "A project with the name " + context.Text + " already exists. Cannot proceed, reverting.";
        var invalidCharacterReverting =
            "TrackedProject names cannot contain \\ or / characters. Cannot proceed, reverting.";
        if (context.Text.Contains("/") || context.Text.Contains("\\"))
            await DisplayAlert("User Error!", invalidCharacterReverting, "Ok");
        bool found;
        var result = Constants.ctx.Projects.Where(p => p.Name == context.Text);
        found = result.Any();
        if (found)
        {
            await DisplayAlert("User Error!", existsReverting, "Ok");
        }
        else
        {
            var oldPath = Constants.GetOrCreatePath(TrackedProject.Name, "");
            fio.FileSystem.RenameDirectory(oldPath, context.Text);
            TrackedProject.Name = context.Text;
        }

        context.Text = "";
    }

    private async void OnFileDeleted(object sender, EventArgs eventArgs)
    {
        var context = (Grid)sender;
        var file = (FileMeta)context.BindingContext;
        var question = "Are you sure to want to Permanently Delete " + file.Filename;
        var answer = await DisplayAlert("Question?", question, "Yes", "No");
        if (answer)
        {
            var targetFile = Constants.GetOrCreatePath(TrackedProject.Name, file.Filename);
            if (File.Exists(targetFile))
                File.Delete(targetFile);
            Constants.ctx.Files.Remove(file);
            await Constants.ctx.SaveChangesAsync();
        }
    }

    private async void OnFileAdd(object sender, EventArgs eventArgs)
    {
        var customFileType = new FilePickerFileType(
            new Dictionary<DevicePlatform, IEnumerable<string>>
            {
                { DevicePlatform.Android, new[] { "application/octet-stream", "application/kml" } }, // MIME type
                { DevicePlatform.WinUI, new[] { ".sor", ".sod", "kml" } }, // file extension
                { DevicePlatform.macOS, new[] { "sor", "sod", "kml" } } // UTType values
            });

        PickOptions options = new()
        {
            PickerTitle = "Please select a file",
            FileTypes = customFileType
        };
        try
        {
            var results = await FilePicker.PickMultipleAsync(options);
            foreach (var result in results)
                if (result.FileName.EndsWith("sor", StringComparison.OrdinalIgnoreCase) ||
                    result.FileName.EndsWith("sod", StringComparison.OrdinalIgnoreCase) ||
                    result.FileName.EndsWith("kml", StringComparison.OrdinalIgnoreCase)
                   )
                {
                    var file = new FileMeta()
                    {
                        DateAdded = DateTime.Now,
                        Filename = result.FileName,
                        ProjectId = TrackedProject.ProjectId,
                        Project = TrackedProject
                    };
                    using var inputStream = await result.OpenReadAsync();
                    var targetFile = Constants.GetOrCreatePath(TrackedProject.Name, result.FileName);
                    if (!File.Exists(targetFile))
                    {
                        using var outputStream = File.Create(targetFile);
                        await inputStream.CopyToAsync(outputStream);
                    }

                    await Constants.ctx.Files.AddAsync(file);
                    if (TrackedProject != null && TrackedProject.Files.Count < 1)
                    {
                        var otdrFile = await Constants.ReadOTDRFileAsync(TrackedProject.Name, result.FileName);
                        Constants.UpdateProjectUsingFile(TrackedProject, otdrFile);
                    }

                    await Constants.ctx.SaveChangesAsync();
                }
        }
        catch (Exception ex)
        {
            // The user canceled or something went wrong
        }
    }

    private async void OnPickerSelectedIndexChanged(object sender, EventArgs e)
    {
        var picker = (Picker)sender;
        var selectedIndex = picker.SelectedIndex;

        switch (selectedIndex)
        {
            case 1:
                await GoToTrace(picker);
                break;
            default:
                break;
        }
    }

    private async void GoToProjects(object sender, TappedEventArgs eventArgs)
    {
        await Constants.ctx.SaveChangesAsync();
        await Shell.Current.GoToAsync("..");
    }

    private async Task GoToTrace(Picker picker)
    {
        if (TrackedProject.Files is { Count: > 0 })
        {
            await Constants.ctx.SaveChangesAsync();
            await Shell.Current.GoToAsync("../projectTrace");
        }
        else
        {
            var question = "There are no files to display";
            await DisplayAlert("Notice", question, "Ok");
            await Constants.ctx.SaveChangesAsync();
            picker.SelectedIndex = 0;
        }
    }

    protected override bool OnBackButtonPressed()
    {
        Constants.ctx.SaveChanges();
        return false;
    }

    public ProjectOverviewPage()
    {
        Constants.ctx.Projects.Load();
        Constants.ctx.Contacts.Load();
        Constants.ctx.Customers.Load();
        Constants.ctx.Locations.Load();
        Constants.ctx.Files.Load();
        InitializeComponent();
        BindingContext = TrackedProject;
        picker.SelectedIndex = 0;
    }
}