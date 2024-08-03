using CommunityToolkit.Mvvm.ComponentModel;
using System.ComponentModel.DataAnnotations.Schema;

namespace OpenOTDR.Models;


public partial class Project : ObservableObject
{
    public int ProjectId { get; set; }
    public bool IsDefault { get; set; } = false;

    [Column("Name")]
    [ObservableProperty] private string name = String.Empty;

    public ICollection<FileMeta> Files { get; }
    public int CustomerId { get; set; }
    public Customer Customer { get; set; }
    public int AId { get; set; }
    public Location A { get; set; }
    public int BId { get; set; }
    public Location B { get; set; }

}