import streamlit as st
import pandas as pd
import uuid
import boto3
import os

# Initialize Boto3 client
connect_client = boto3.client("connect")

# Set page configuration
st.set_page_config(
    page_title="Amazon Connect Management Portal",
    layout="wide",
    initial_sidebar_state="expanded"
)

# File paths for saved selections
SELECTED_REGIONS_FILE = "selected_regions.csv"
SELECTED_INSTANCES_FILE = "selected_instances.csv"
INSTANCES_CACHE_FILE = "instances_cache.csv"

# Define AWS regions where Amazon Connect is available
# Using a dictionary to map region codes to their display names
CONNECT_REGION_MAP = {
    "us-east-1": "us-east-1 (N. Virginia)",
    "us-west-2": "us-west-2 (Oregon)",
    "ap-northeast-1": "ap-northeast-1 (Tokyo)",
    "ap-northeast-2": "ap-northeast-2 (Seoul)",
    "ap-southeast-1": "ap-southeast-1 (Singapore)",
    "ap-southeast-2": "ap-southeast-2 (Sydney)",
    "eu-central-1": "eu-central-1 (Frankfurt)",
    "eu-west-2": "eu-west-2 (London)",
    "af-south-1": "af-south-1 (Cape Town)",
    "ca-central-1": "ca-central-1 (Canada Central)"
}

# Get region codes (to use as values) and display names (to show in the dropdown)
REGION_CODES = list(CONNECT_REGION_MAP.keys())
REGION_DISPLAY_NAMES = list(CONNECT_REGION_MAP.values())

# Initialize session state for selected instance and form visibility
if 'selected_instance' not in st.session_state:
    st.session_state['selected_instance'] = None
if 'show_account_form' not in st.session_state:
    st.session_state['show_account_form'] = False
if 'show_routing_form' not in st.session_state:
    st.session_state['show_routing_form'] = False
if 'show_quickconnect_form' not in st.session_state:
    st.session_state['show_quickconnect_form'] = False
if 'instances_df' not in st.session_state:
    st.session_state['instances_df'] = None

# Function to load saved regions from CSV


def load_saved_regions():
    if os.path.exists(SELECTED_REGIONS_FILE):
        try:
            regions_df = pd.read_csv(SELECTED_REGIONS_FILE)
            if 'region' in regions_df.columns:
                return regions_df['region'].tolist()
        except Exception as e:
            st.warning(f"Error loading saved regions: {e}")
    return ["us-east-1"]  # Default to us-east-1 if no saved regions or error

# Function to save selected regions to CSV


def save_regions_to_csv(regions):
    try:
        regions_df = pd.DataFrame({'region': regions})
        regions_df.to_csv(SELECTED_REGIONS_FILE, index=False)
    except Exception as e:
        st.warning(f"Error saving regions: {e}")

# Function to load saved instances from CSV


def load_saved_instances():
    if os.path.exists(SELECTED_INSTANCES_FILE):
        try:
            instances_df = pd.read_csv(SELECTED_INSTANCES_FILE)
            if 'instance_id' in instances_df.columns:
                return instances_df['instance_id'].tolist()
        except Exception as e:
            st.warning(f"Error loading saved instances: {e}")
    return []

# Function to save selected instances to CSV


def save_instances_to_csv(instance_ids):
    try:
        instances_df = pd.DataFrame({'instance_id': instance_ids})
        instances_df.to_csv(SELECTED_INSTANCES_FILE, index=False)
    except Exception as e:
        st.warning(f"Error saving instances: {e}")

# Function to generate mock Connect instances or fetch real ones


def generate_mock_instances(regions):
    # First check if we have cached results
    if os.path.exists(INSTANCES_CACHE_FILE):
        try:
            cached_df = pd.read_csv(INSTANCES_CACHE_FILE)
            # Filter by the selected regions
            cached_df = cached_df[cached_df['Region'].isin(regions)]
            if not cached_df.empty:
                return cached_df
        except Exception:
            # If there's an error loading the cache, continue to fetch new data
            pass

    instances = []
    for region in regions:
        try:
            connect = boto3.client('connect', region_name=region)
            res = connect.list_instances()
            for i in res['InstanceSummaryList']:
                instances.append({
                    "Instance ID": i['Id'],
                    "Region": region,
                    "Instance Alias": i.get('InstanceAlias', 'No Alias')
                })
        except Exception as e:
            # If there's an error fetching instances, create mock data
            st.warning(f"Error fetching instances for region {region}: {e}")
            for i in range(1, 4):
                instance_id = f"instance-{uuid.uuid4().hex[:8]}"
                instances.append({
                    "Instance ID": instance_id,
                    "Region": region,
                    "Instance Alias": f"MockInstance-{i}"
                })

    instances_df = pd.DataFrame(instances)

    # Cache the results for future use
    if not instances_df.empty:
        try:
            instances_df.to_csv(INSTANCES_CACHE_FILE, index=False)
        except Exception:
            pass

    return instances_df

# Functions to toggle form visibility


def toggle_account_form():
    st.session_state['show_account_form'] = not st.session_state['show_account_form']


def toggle_routing_form():
    st.session_state['show_routing_form'] = not st.session_state['show_routing_form']


def toggle_quickconnect_form():
    st.session_state['show_quickconnect_form'] = not st.session_state['show_quickconnect_form']


# Main title
st.title("Amazon Connect Management Portal")

# Load previously selected regions from CSV
default_regions = load_saved_regions()

# Convert default regions to display names for the multiselect
default_display_regions = [CONNECT_REGION_MAP[r]
                           for r in default_regions if r in CONNECT_REGION_MAP]

# Multi-select box for regions with formatted display names
selected_display_regions = st.multiselect(
    "Select Connect Regions",
    REGION_DISPLAY_NAMES,
    default=default_display_regions
)

# Convert the selected display names back to region codes
selected_regions = [key for key, value in CONNECT_REGION_MAP.items()
                    if value in selected_display_regions]

# Save the selected regions to CSV when they change
if selected_regions != default_regions:
    save_regions_to_csv(selected_regions)

# Display Connect instances based on selected regions
if selected_regions:
    # If instances haven't been loaded yet, or if the selected regions changed
    if st.session_state['instances_df'] is None or set(selected_regions) != set(default_regions):
        st.session_state['instances_df'] = generate_mock_instances(
            selected_regions)

    instances_df = st.session_state['instances_df']

    # Create a dictionary mapping instance_id to display name (instance_id, region)
    instance_display_map = {}
    for idx, row in instances_df.iterrows():
        instance_id = row["Instance ID"]
        instance_alias = row["Instance Alias"]
        region = row["Region"]
        display_name = f"{instance_id}, {instance_alias}, {CONNECT_REGION_MAP[region]}"
        instance_display_map[instance_id] = display_name

    # Create a list of instance IDs and their display names
    instance_ids = list(instance_display_map.keys())

    # Load previously selected instances
    default_instances = load_saved_instances()
    # Filter to ensure only valid instances are selected
    default_instances = [i for i in default_instances if i in instance_ids]

    # Create a multi-select box for instances
    selected_instance_ids = st.multiselect(
        "Select Connect Instances",
        options=instance_ids,
        default=default_instances,
        format_func=lambda x: instance_display_map[x]
    )

    # Save the selected instances to CSV when they change
    if set(selected_instance_ids) != set(default_instances):
        save_instances_to_csv(selected_instance_ids)

    # Tabs for different management sections
    tabs = st.tabs(
        ["Account Management", "Routing Profile Management", "Quick Connect Management"])

    # Account Management Tab
    with tabs[0]:
        st.header("Account Management")

        # Add button to show/hide the form
        st.button("Add New Account", on_click=toggle_account_form)

        # Show form only if the button was clicked
        if st.session_state['show_account_form']:
            with st.form("account_form"):
                st.subheader("Add/Edit Account")
                username = st.text_input("Username")
                email = st.text_input("Email Address")
                role = st.selectbox("Role", ["Admin", "Agent", "Supervisor"])
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input(
                    "Confirm Password", type="password")

                col1, col2 = st.columns([1, 5])
                with col1:
                    submitted = st.form_submit_button("Save Account")
                with col2:
                    if submitted:
                        if password != confirm_password:
                            st.error("Passwords do not match")
                        else:
                            st.success(
                                f"Account {username} saved successfully!")
                            # Hide the form after successful save
                            st.session_state['show_account_form'] = False

        # Display mock account data
        st.subheader("Existing Accounts")
        accounts_data = {
            "Email": ["agent1@example.com", "supervisor1@example.com", "admin1@example.com"],
            "Username": ["agent1", "supervisor1", "admin1"],
            "First Name": ["agent1", "supervisor1", "admin1"],
            "Last Name": ["test", "test", "test"],
            "User Group": ["AG1", "AG2", "AG3"],
            "Routing Profile": ["Agent", "Supervisor", "Admin"],
            "Quick Connect": ["agent1", "supervisor1", "admin1"],
            "Instance": ["instance-56a4e02c", "instance-56a4e02c", "instance-56a4e02c"]
        }
        st.dataframe(pd.DataFrame(accounts_data))

    # Routing Profile Management Tab
    with tabs[1]:
        st.header("Routing Profile Management")

        # Add button to show/hide the form
        st.button("Add New Routing Profile", on_click=toggle_routing_form)

        # Show form only if the button was clicked
        if st.session_state['show_routing_form']:
            with st.form("routing_profile_form"):
                st.subheader("Add/Edit Routing Profile")
                profile_name = st.text_input("Profile Name")
                description = st.text_area("Description")

                # Mock queue selection
                queues = st.multiselect(
                    "Queues",
                    ["BasicQueue", "PremiumQueue", "SupportQueue", "SalesQueue"]
                )

                # Priority settings for each selected queue
                if queues:
                    st.subheader("Queue Priorities")
                    priorities = {}
                    for queue in queues:
                        priorities[queue] = st.slider(
                            f"Priority for {queue}", 1, 10, 5)

                col1, col2 = st.columns([1, 5])
                with col1:
                    submitted = st.form_submit_button("Save Routing Profile")
                with col2:
                    if submitted:
                        st.success(
                            f"Routing profile {profile_name} saved successfully!")
                        # Hide the form after successful save
                        st.session_state['show_routing_form'] = False

        # Display mock routing profile data
        st.subheader("Existing Routing Profiles")
        profiles_data = {
            "Name": ["Default Profile", "Sales Profile", "Support Profile"],
            "Description": ["Default routing", "For sales team", "For support team"],
            "Queues": ["BasicQueue", "SalesQueue, PremiumQueue", "SupportQueue, BasicQueue"],
            "Default Outbound Queue": ["BasicQueue", "SalesQueue", "SupportQueue"]
        }
        st.dataframe(pd.DataFrame(profiles_data))

    # Quick Connect Management Tab
    with tabs[2]:
        st.header("Quick Connect Management")

        # Add button to show/hide the form
        st.button("Add New Quick Connect", on_click=toggle_quickconnect_form)

        # Show form only if the button was clicked
        if st.session_state['show_quickconnect_form']:
            with st.form("quick_connect_form"):
                st.subheader("Add/Edit Quick Connect")
                quick_connect_name = st.text_input("Quick Connect Name")

                qc_type = st.selectbox(
                    "Type",
                    ["User", "Queue", "Phone Number"]
                )

                if qc_type == "User":
                    st.selectbox("User", ["agent1", "supervisor1", "admin1"])
                elif qc_type == "Queue":
                    st.selectbox(
                        "Queue", ["BasicQueue", "PremiumQueue", "SupportQueue", "SalesQueue"])
                elif qc_type == "Phone Number":
                    st.text_input("Phone Number")

                description = st.text_area("Description")

                col1, col2 = st.columns([1, 5])
                with col1:
                    submitted = st.form_submit_button("Save Quick Connect")
                with col2:
                    if submitted:
                        st.success(
                            f"Quick connect {quick_connect_name} saved successfully!")
                        # Hide the form after successful save
                        st.session_state['show_quickconnect_form'] = False

        # Display mock quick connect data
        st.subheader("Existing Quick Connects")
        quick_connects_data = {
            "Name": ["Support", "Sales Manager", "Helpdesk"],
            "Type": ["Queue", "User", "Phone Number"],
            "Destination": ["SupportQueue", "supervisor1", "+1-555-123-4567"],
            "Description": ["Support team", "Sales escalations", "External helpdesk"]
        }
        st.dataframe(pd.DataFrame(quick_connects_data))
else:
    st.warning("Please select at least one AWS region.")

# Add footer
st.markdown("---")
st.caption("Amazon Connect Management Portal © 2025")
