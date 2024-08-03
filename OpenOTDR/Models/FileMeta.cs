using CommunityToolkit.Mvvm.ComponentModel;
using System.ComponentModel.DataAnnotations.Schema;
using OpenOTDR.Services;
using OTDRFile = BaldrAI.OpenOTDR.OTDRFile.OTDRFile;

namespace OpenOTDR.Models;

public partial class FileMeta: ObservableObject
{
    public int FileMetaId { get; set; }

    [Column("Filename")]
    [ObservableProperty] private string filename = string.Empty;

    public string FileType => Filename.Split(".").Last().ToUpper();

    public string DateAddedStr => DateAdded.Year + "-" + DateAdded.Month + "-" + DateAdded.Day + " " +
                                  DateAdded.ToShortTimeString();
    [Column("DateAdded")]
    [ObservableProperty] private DateTime dateAdded = DateTime.Now;

    public string Wavelength
    {
        get
        {
            string wavelength = "N/A";
            if (Filename.EndsWith("sor", StringComparison.OrdinalIgnoreCase) ||
                Filename.EndsWith("sod", StringComparison.OrdinalIgnoreCase))
            {
                wavelength = OTDRFile.GenParams.Wavelength.ToString();
            }
            return wavelength;
        }
    }

    [NotMapped] public OTDRFile? _file;

    public OTDRFile OTDRFile
    {
        get
        {
            if (_file == null)
                _file = Constants.ReadOTDRFile(Project.Name, Filename);
            return _file;
        }
    }
    public int ProjectId { get; set; }
    public Project Project { get; set; } = null!;

};
