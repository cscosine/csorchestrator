from csorchestrator.domain.context.context_compiler_generator import (
    Compiler,
    ContextCompilerGenerator,
    GeneratorType,
    GeneratorWithType,
)
from csorchestrator.domain.context.context_os_architecture import (
    ARCHITECTURE_VARIANT_GENERIC,
    OS,
    Architecture,
    ContextOsArchitecture,
    UbuntuVersions,
    WindowsVersions,
)
from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    ContextOsArchitectureCompilerGenerator,
)
from csorchestrator.frontend.cscmake_presets.supported_variants import (
    BuildConfig,
    get_all_supported_workflow_descriptions,
    get_supported_os_version_list,
    is_config_selected_for_generator,
    is_config_selected_multi_config_generator,
    is_config_selected_single_config_generator,
    workflow_name_from_description,
)


def test_is_config_selected_multi_config_generator() -> None:

    assert is_config_selected_multi_config_generator(BuildConfig.DEBUG, BuildConfig.DEBUG)
    assert is_config_selected_multi_config_generator(BuildConfig.RELEASE, BuildConfig.RELEASE)
    assert is_config_selected_multi_config_generator(BuildConfig.RELWITHDEBINFO, BuildConfig.RELWITHDEBINFO)
    assert is_config_selected_multi_config_generator(BuildConfig.PARANOID, BuildConfig.PARANOID)
    assert is_config_selected_multi_config_generator(BuildConfig.DEBUG_RELEASE, BuildConfig.DEBUG_RELEASE)
    assert is_config_selected_multi_config_generator(
        BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID,
        BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID,
    )

    assert not is_config_selected_multi_config_generator(BuildConfig.RELEASE, BuildConfig.DEBUG)
    assert not is_config_selected_multi_config_generator(BuildConfig.DEBUG_RELEASE, BuildConfig.DEBUG)
    assert not is_config_selected_multi_config_generator(BuildConfig.DEBUG_RELEASE, BuildConfig.RELEASE)

    assert not is_config_selected_multi_config_generator(current_config="INVALID", requested_config=BuildConfig.DEBUG)  # type: ignore
    assert not is_config_selected_multi_config_generator(current_config=BuildConfig.DEBUG, requested_config="INVALID")  # type: ignore
    assert not is_config_selected_multi_config_generator(current_config="INVALID", requested_config="INVALID")  # type: ignore


def test_is_config_selected_for_generator() -> None:
    assert is_config_selected_for_generator(
        GeneratorType.SINGLE_CONFIG,
        current_config=BuildConfig.DEBUG,
        requested_config=BuildConfig.DEBUG,
    )
    assert not is_config_selected_for_generator(
        GeneratorType.SINGLE_CONFIG,
        current_config=BuildConfig.DEBUG,
        requested_config=BuildConfig.PARANOID,
    )

    assert is_config_selected_for_generator(
        GeneratorType.MULTI_CONFIG,
        current_config=BuildConfig.DEBUG,
        requested_config=BuildConfig.DEBUG,
    )
    assert not is_config_selected_for_generator(
        GeneratorType.MULTI_CONFIG,
        current_config=BuildConfig.DEBUG,
        requested_config=BuildConfig.PARANOID,
    )


def test_is_config_selected_single_config_generator() -> None:

    # single config request are ok if they exactly match the current config
    assert is_config_selected_single_config_generator(
        current_config=BuildConfig.DEBUG, requested_config=BuildConfig.DEBUG
    )
    assert is_config_selected_single_config_generator(
        current_config=BuildConfig.RELEASE, requested_config=BuildConfig.RELEASE
    )
    assert is_config_selected_single_config_generator(
        current_config=BuildConfig.RELWITHDEBINFO,
        requested_config=BuildConfig.RELWITHDEBINFO,
    )
    assert is_config_selected_single_config_generator(
        current_config=BuildConfig.PARANOID, requested_config=BuildConfig.PARANOID
    )

    assert not is_config_selected_single_config_generator(
        current_config=BuildConfig.DEBUG, requested_config=BuildConfig.RELEASE
    )
    assert not is_config_selected_single_config_generator(
        current_config=BuildConfig.RELWITHDEBINFO, requested_config=BuildConfig.PARANOID
    )

    # if we request debug release, both debug and release are ok
    assert is_config_selected_single_config_generator(
        current_config=BuildConfig.DEBUG, requested_config=BuildConfig.DEBUG_RELEASE
    )
    assert is_config_selected_single_config_generator(
        current_config=BuildConfig.RELEASE, requested_config=BuildConfig.DEBUG_RELEASE
    )
    assert not is_config_selected_single_config_generator(
        current_config=BuildConfig.PARANOID, requested_config=BuildConfig.DEBUG_RELEASE
    )
    assert not is_config_selected_single_config_generator(
        current_config=BuildConfig.RELWITHDEBINFO,
        requested_config=BuildConfig.DEBUG_RELEASE,
    )

    # if we request all, all are ok
    assert is_config_selected_single_config_generator(
        current_config=BuildConfig.DEBUG,
        requested_config=BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID,
    )
    assert is_config_selected_single_config_generator(
        current_config=BuildConfig.RELEASE,
        requested_config=BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID,
    )
    assert is_config_selected_single_config_generator(
        current_config=BuildConfig.PARANOID,
        requested_config=BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID,
    )
    assert is_config_selected_single_config_generator(
        current_config=BuildConfig.RELWITHDEBINFO,
        requested_config=BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID,
    )
    assert not is_config_selected_single_config_generator(
        current_config=BuildConfig.DEBUG_RELEASE,
        requested_config=BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID,
    )
    assert not is_config_selected_single_config_generator(
        current_config=BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID,
        requested_config=BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID,
    )

    assert not is_config_selected_single_config_generator(current_config="INVALID", requested_config=BuildConfig.DEBUG)  # type: ignore
    assert not is_config_selected_single_config_generator(current_config=BuildConfig.DEBUG, requested_config="INVALID")  # type: ignore
    assert not is_config_selected_single_config_generator(current_config="INVALID", requested_config="INVALID")  # type: ignore


def test_get_all_supported_workflow_descriptions() -> None:
    context = ContextOsArchitectureCompilerGenerator(
        context_os_architecture=ContextOsArchitecture(
            os=OS.LINUX,
            os_version=UbuntuVersions.UBUNTU_22_04.value,
            architecture=Architecture.X64,
            architecture_variant=ARCHITECTURE_VARIANT_GENERIC,
        ),
        context_compiler_generator=ContextCompilerGenerator(
            compiler_family=Compiler.GCC,
            compiler_version=ContextCompilerGenerator.COMPILER_VERSION_DEFAULT,
            build_generator=GeneratorWithType.NINJA,
        ),
    )

    assert len(get_all_supported_workflow_descriptions(BuildConfig.DEBUG, context)) > 0
    assert len(get_all_supported_workflow_descriptions(BuildConfig.RELEASE, context)) > 0
    assert len(get_all_supported_workflow_descriptions(BuildConfig.RELWITHDEBINFO, context)) > 0
    assert len(get_all_supported_workflow_descriptions(BuildConfig.PARANOID, context)) > 0
    assert len(get_all_supported_workflow_descriptions(BuildConfig.DEBUG_RELEASE, context)) > 0
    assert len(get_all_supported_workflow_descriptions(BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID, context)) > 0

    list = get_all_supported_workflow_descriptions(BuildConfig.DEBUG, context)
    for desc in list:
        name = workflow_name_from_description(desc)
        assert name.startswith("workflow-")
        assert name.endswith("-debug")


def test_get_supported_os_version_list() -> None:
    linux_versions = get_supported_os_version_list(OS.LINUX)
    assert len(linux_versions) > 0
    assert UbuntuVersions.UBUNTU_24_04.value in linux_versions

    windows_versions = get_supported_os_version_list(OS.WINDOWS)
    assert len(windows_versions) > 0
    assert WindowsVersions.WIN10.value in windows_versions

    macos_versions = get_supported_os_version_list(OS.MACOS)
    assert len(macos_versions) == 0  # TODO add MACOS support
