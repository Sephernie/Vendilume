ADMINISTRATORS = "Administrators"
SALES_ANALYSTS = "Sales Analysts"
MANAGERS = "Managers"


ROLE_PERMISSIONS = {
    ADMINISTRATORS: (
        ("datasets", "add_dataset"),
        ("datasets", "change_dataset"),
        ("datasets", "delete_dataset"),
        ("datasets", "view_dataset"),
        ("auth", "add_user"),
        ("auth", "change_user"),
        ("auth", "delete_user"),
        ("auth", "view_user"),
        ("auth", "add_group"),
        ("auth", "change_group"),
        ("auth", "delete_group"),
        ("auth", "view_group"),
    ),
    SALES_ANALYSTS: (
        ("datasets", "add_dataset"),
        ("datasets", "delete_dataset"),
        ("datasets", "view_dataset"),
    ),
    MANAGERS: (
        ("datasets", "view_dataset"),
    ),
}
