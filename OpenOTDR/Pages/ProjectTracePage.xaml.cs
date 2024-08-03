using OTDRFile = BaldrAI.OpenOTDR.OTDRFile.OTDRFile;
using fio = Microsoft.VisualBasic.FileIO;
using OpenOTDR.Models;
using OpenOTDR.Services;
using Microsoft.EntityFrameworkCore;
using Microsoft.Maui.Storage;
using OpenOTDR.ViewModels;

namespace OpenOTDR.Pages;


public partial class ProjectTracePage : ContentPage
{
    public Project TrackedProject => ProjectsContext.TrackedProject;
    public ChartData ChartData;

    public List<OTDRFile> OtdrFiles
    {
        get;
        set;
    } = new ();

    async void OnPickerSelectedIndexChanged(object sender, EventArgs e)
    {
        var picker = (Picker)sender;
        int selectedIndex = picker.SelectedIndex;

        switch (selectedIndex)
        {
            case 0:
                await GoToOverview();
                break;
            default:
                break;
        }
    }

    async void GoToProjects(object? sender, EventArgs eventArgs)
    {
        await Constants.ctx.SaveChangesAsync();
        await Shell.Current.GoToAsync("..");
    }

    async Task GoToOverview()
    {
        await Constants.ctx.SaveChangesAsync();
        await Shell.Current.GoToAsync("../projectOverview");
    }

    protected override bool OnBackButtonPressed()
    {
        Constants.ctx.SaveChanges();
        return false;
    }

    private void PopulateMetadata()
    {
        var otdr = TrackedProject.Files.First().OTDRFile;
        MetaCircuitId.Text = otdr.GenParams.FiberId + "/" + otdr.GenParams.CableId;
        if (otdr.KeyEvents.EndToEndLoss == 0.0)
        {
            var firstEvent = otdr.KeyEvents.Events.First();
            var firstIndex = (int)(firstEvent.DistanceMeters / otdr.FxdParams.Resolution[0]);
            var firstPoint = otdr.DataPts.Traces[0].DataPoints[firstIndex];
            var lastEvent = otdr.KeyEvents.Events.Last();
            var lastIndex = (int)(lastEvent.DistanceMeters / otdr.FxdParams.Resolution[0]);
            var lastPoint = otdr.DataPts.Traces[0].DataPoints[lastIndex];
            MetaE2ELoss.Text = (lastPoint - firstPoint).ToString();
        }
        else
            MetaE2ELoss.Text = otdr.KeyEvents.EndToEndLoss.ToString();
        MetaFiberType.Text = $"ITU-G.{otdr.GenParams.FiberType}";
        if (otdr.KeyEvents.NumberOfEvents > 0)
        {
            double distance = otdr.FxdParams.Units == "km" ? Math.Round(otdr.KeyEvents.Events.Last().Distance, 2) : Math.Round(otdr.KeyEvents.Events.Last().Distance / 1000, 2);
            MetaLength.Text = distance + "km";
        }
        MetaIOR.Text = otdr.FxdParams.IndexOfRefraction.ToString();
        MetaLocA.Text = otdr.GenParams.LocationA;
        MetaLocB.Text = otdr.GenParams.LocationB;
        MetaModel.Text = otdr.SupParams.SupplierName + " " + otdr.SupParams.OtdrName + " (" +
                         otdr.SupParams.SoftwareVersion + ") - " + otdr.SupParams.OtdrSerialNumber;
        MetaOperator.Text = otdr.GenParams.Operator;
        MetaPulseWidth.Text = otdr.FxdParams.PulseWidth[0] + "ns";
        if (otdr.FxdParams.AcquisitionRangeDistance == 0)
            otdr.FxdParams.AcquisitionRange = (int)otdr.FxdParams.AcquisitionRange;
        double rangeDistance = otdr.FxdParams.Units == "km" ? Math.Round(otdr.FxdParams.AcquisitionRangeDistance, 0) : Math.Round(otdr.FxdParams.AcquisitionRangeDistance/1000, 0);
        MetaRange.Text = rangeDistance + "km";
        MetaResolution.Text = $"{otdr.FxdParams.Resolution[0]:F2}m" ;
        List<string> wavelengths = new();
        List<string> filenames = new();
        foreach (var fileMeta in TrackedProject.Files)
        {
            wavelengths.Add(fileMeta.Wavelength + "nm");
            filenames.Add(fileMeta.Filename);
        }
        MetaWavelength.Text = string.Join(", ", wavelengths);
        MetaFiles.Text = string.Join(", ", filenames);
    }

    public ProjectTracePage()
    {
        Constants.ctx.Projects.Load();
        Constants.ctx.Contacts.Load();
        Constants.ctx.Customers.Load();
        Constants.ctx.Locations.Load();
        Constants.ctx.Files.Load();
        InitializeComponent();
        picker.SelectedIndex = 1;
        ChartData = new ChartData(TrackedProject.Files);
        Chart.BindingContext = ChartData;
        DataGrid.ItemsSource = TrackedProject.Files.First().OTDRFile.KeyEvents.Events;
        PopulateMetadata();
        BindingContext = TrackedProject;
    }

}

