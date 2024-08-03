
using CommunityToolkit.Mvvm.ComponentModel;
using System.ComponentModel.DataAnnotations.Schema;

namespace OpenOTDR.Models;

public partial class Contact: ObservableObject
{
    public int ContactId { get; set; }
    public string DisplayName
    {
        get
        {
            return FirstName + " " + LastName;
        }

        set
        { var parts = value.Split(' ');
            FirstName = parts[0];
            LastName = string.Join(" ", parts.Skip(1).ToArray()); ;
        }
    }

    [Column("FirstName")]
    [ObservableProperty] private string firstName = string.Empty;

    [Column("LastName")]
    [ObservableProperty] private string lastName = string.Empty;

    [Column("Email")]
    [ObservableProperty]
    private string email = string.Empty;

    [Column("Phone")]
    [ObservableProperty] private string phone = string.Empty;
}
