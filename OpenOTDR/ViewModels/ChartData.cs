using CommunityToolkit.Mvvm.ComponentModel;
using LiveChartsCore;
using LiveChartsCore.Defaults;
using LiveChartsCore.SkiaSharpView;
using LiveChartsCore.SkiaSharpView.Painting;
using OpenOTDR.Models;
using BaldrAI.OpenOTDR.OTDRFile.Internal;
using SkiaSharp;

namespace OpenOTDR.ViewModels;

public partial class ChartData : ObservableObject
{
    
    public ICollection<FileMeta> Files;

    public ISeries[] Series { get; set; }

    private static List<ObservablePoint> Fetch(FileMeta file)
    {
        var list = new List<ObservablePoint>();
        var increment = 10;
        var limit = file.OTDRFile.DataPts.Traces[0].DataPoints.Count - increment;
        for (var x=0; x<=limit; x+=increment )
        {
            var y = (float)file.OTDRFile.DataPts.Traces[0].DataPoints[x];
            var distance = x * file.OTDRFile.FxdParams.Resolution[0];
            list.Add(new ObservablePoint(distance, -y));
        }

        return list;
    }

    public ChartData(ICollection<FileMeta> files)
    {
        Files = files;
        Series = new ISeries[Files.Count];
        for (int i = 0; i < Files.Count; i++)
        {
            var file = Files.ElementAt(i);
            float mappedHue = ((float)file.OTDRFile.FxdParams.Wavelength).Remap((float)800.0, (float)2000.0, (float)0.0, (float)360.0);
            Series[i] = new LineSeries<ObservablePoint>
            {
                Name = $"{file.OTDRFile.FxdParams.Wavelength}nm",
                Values = Fetch(file),
                Fill = null,
                Stroke = new SolidColorPaint(SKColor.FromHsl(mappedHue, 100f,50f), 1),
                GeometryStroke = new SolidColorPaint(SKColor.FromHsl(mappedHue, 100f, 50f), 0),
                GeometrySize = 0,
                LineSmoothness = 0, 
            };
        }
    }

    public Axis[] XAxes { get; set; } =
    {
        new Axis
        {
            CrosshairLabelsBackground = SKColors.DarkOrange.AsLvcColor(),
            CrosshairLabelsPaint = new SolidColorPaint(SKColors.DarkRed, 1),
            CrosshairPaint = new SolidColorPaint(SKColors.DarkOrange, 1),
            Labeler = value => value.ToString("F1")
        }
    };
    public Axis[] YAxes { get; set; } =
    {
        new Axis
        {
            Labeler = value => value.ToString("F1")
        }
    };
}

