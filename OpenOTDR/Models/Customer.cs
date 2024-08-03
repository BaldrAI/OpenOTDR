using CommunityToolkit.Mvvm.ComponentModel;
using System.ComponentModel.DataAnnotations.Schema;

namespace OpenOTDR.Models;

public partial class Customer: ObservableObject
{
    public int CustomerId { get; set; }

    [Column("Name")]
    [ObservableProperty] private string? name = string.Empty;

    [Column("Address")]
    [ObservableProperty] private string? address = string.Empty;
    public Contact? TechnicalContact  { get; set; }
    public Contact? BillingContact  { get; set; }

};