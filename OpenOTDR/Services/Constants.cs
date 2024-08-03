using OpenOTDR.Models;
using OTDRFile = BaldrAI.OpenOTDR.OTDRFile.OTDRFile;
using Location = OpenOTDR.Models.Location;

namespace OpenOTDR.Services;

public static class Constants
{
    public const string DatabaseFilename = "OpenOTDR.db3";

    public static string DatabasePath =>
        Path.Combine(FileSystem.AppDataDirectory, DatabaseFilename);

    public static ProjectsContext ctx;

    public static string GetOrCreatePath(string projectName, string fileName)
    {
        var projectDir = Path.Combine(FileSystem.Current.AppDataDirectory, projectName);
        if (!Directory.Exists(projectDir))
            Directory.CreateDirectory(projectDir);
        return Path.Combine(projectDir, fileName);
    }

    public static OTDRFile ReadOTDRFile(string projectName, string fileName)
    {
        byte[] b;
        var projectDir = Path.Combine(FileSystem.Current.AppDataDirectory, projectName);
        using (var fs = File.Open(Path.Combine(projectDir, fileName), FileMode.Open))
        {
            b = new byte[fs.Length];
            fs.Read(b, 0, b.Length);
        }
        return new OTDRFile(b);
    }

    public static async Task<OTDRFile> ReadOTDRFileAsync(string projectName, string fileName)
    {
        byte[] b;
        var projectDir = Path.Combine(FileSystem.Current.AppDataDirectory, projectName);
        using (var fs = File.Open(Path.Combine(projectDir, fileName), FileMode.Open))
        {
            b = new byte[fs.Length];
            await fs.ReadAsync(b, 0, b.Length);
        }

        return new OTDRFile(b);
    }


    public static void UpdateProjectUsingFile(Project trackedProject, OTDRFile file)
    {
        foreach (var (address, loc) in new Dictionary<string, Location>()
                 {
                     {
                         file.GenParams.LocationA, trackedProject.A
                     },
                     {
                         file.GenParams.LocationB, trackedProject.B
                     }
                 })

        {
            if (loc.Address == string.Empty)
                loc.Address = address;
            if (loc.CableIn == string.Empty)
                loc.CableIn = file.GenParams.CableId;
            if (loc.FibreIn == string.Empty)
                loc.FibreIn = file.GenParams.FiberId;
            if (loc.CableOut == string.Empty)
                loc.CableOut = file.GenParams.CableId;
            if (loc.FibreOut == string.Empty)
                loc.FibreOut = file.GenParams.FiberId;
        }
    }
}